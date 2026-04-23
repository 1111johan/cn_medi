from __future__ import annotations

import re
from typing import Any, Dict, List

from app.core.audit import record_event
from app.core.config import SYNDROME_RULES
from app.services.document_service import document_service
from app.services.feedback_service import feedback_service
from app.services.intake_service import intake_service
from app.services.knowledge_service import knowledge_service
from app.services.professional_knowledge_service import professional_knowledge_service
from app.services.reasoning_service import reasoning_service

DEMO_PATIENTS: List[Dict[str, Any]] = [
    {
        "case_id": "case-20260424-001",
        "patient_id": "P202604001",
        "name": "王某某",
        "gender": "女",
        "age": 45,
        "department": "中医内科",
        "visit_type": "复诊",
        "visit_time": "2026-04-24 09:10",
        "chief_complaint": "失眠2周，伴心烦口干",
        "present_illness": "近2周入睡困难，多梦易醒，夜间烦躁，晨起口干，近3天心烦明显。",
        "tongue": "舌红，苔黄腻",
        "pulse": "滑数",
        "symptoms": ["失眠", "心烦", "口干"],
        "exam_results": "常规检查未见明显异常。",
        "past_history": "否认重大慢病史。",
    },
    {
        "case_id": "case-20260424-002",
        "patient_id": "P202604002",
        "name": "刘某",
        "gender": "男",
        "age": 36,
        "department": "中医内科",
        "visit_type": "初诊",
        "visit_time": "2026-04-24 10:20",
        "chief_complaint": "胸闷痰多1月",
        "present_illness": "胸闷反复1月，咳痰较多，纳差，体倦困重。",
        "tongue": "舌胖，苔白腻",
        "pulse": "滑",
        "symptoms": ["胸闷", "痰多", "纳差", "乏力"],
        "exam_results": "胸片未见明显实变。",
        "past_history": "吸烟10年。",
    },
    {
        "case_id": "case-20260424-003",
        "patient_id": "P202604003",
        "name": "陈某",
        "gender": "女",
        "age": 52,
        "department": "中医内科",
        "visit_type": "复诊",
        "visit_time": "2026-04-24 14:00",
        "chief_complaint": "乏力纳差伴便溏3周",
        "present_illness": "近3周乏力明显，食欲下降，餐后腹胀，大便偏溏。",
        "tongue": "舌淡胖，苔白腻",
        "pulse": "濡涩",
        "symptoms": ["乏力", "纳差", "腹胀", "便溏"],
        "exam_results": "血糖波动偏高。",
        "past_history": "2型糖尿病5年。",
    },
]


class ClinicalService:
    def list_demo_patients(self) -> List[Dict[str, Any]]:
        return DEMO_PATIENTS

    def analyze(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        case_id = str(payload.get("case_id") or "demo-case")
        patient = self._build_patient_card(payload)
        input_summary = self._build_input_summary(payload)

        raw_text = "；".join(
            [
                input_summary.get("chief_complaint", ""),
                input_summary.get("present_illness", ""),
                input_summary.get("tongue", ""),
                input_summary.get("pulse", ""),
                input_summary.get("exam_results", ""),
                input_summary.get("past_history", ""),
            ]
        )
        intake = intake_service.parse(
            raw_text=raw_text,
            form_data={
                "chief_complaint": input_summary.get("chief_complaint", ""),
                "tongue": input_summary.get("tongue", ""),
                "pulse": input_summary.get("pulse", ""),
            },
        )

        symptoms = self._collect_symptoms(payload, intake)
        tongue_tags = self._collect_tags(input_summary.get("tongue", ""), self._all_tongue_tags())
        pulse_tags = self._collect_tags(input_summary.get("pulse", ""), self._all_pulse_tags())
        constraints = {
            "pregnant": "孕" in input_summary.get("past_history", "") or "妊娠" in input_summary.get("past_history", "")
        }

        candidates = reasoning_service.reason_syndrome(
            symptoms=symptoms,
            tongue_tags=tongue_tags,
            pulse_tags=pulse_tags,
            constraints=constraints,
        )
        trace = reasoning_service.reason_trace(
            symptoms=symptoms,
            tongue_tags=tongue_tags,
            pulse_tags=pulse_tags,
            constraints=constraints,
        )
        top_candidate = candidates[0] if candidates else None
        top_score = float(top_candidate.get("score", 0)) if top_candidate else 0.0
        top_syndromes = [
            {
                "name": item["syndrome"],
                "score": self._normalize_score(float(item.get("score", 0))),
                "support_evidence": item.get("support_evidence", [])[:4],
                "counter_evidence": item.get("counter_evidence", [])[:2],
            }
            for item in candidates[:3]
        ]

        rule_hits = [
            {
                "rule_id": f"R{idx + 1:03d}",
                "rule_name": f"{item['syndrome']}辨证规则",
                "matched_evidence": [self._clean_rule_item(x) for x in item.get("support_evidence", [])[:5]],
            }
            for idx, item in enumerate(candidates[:3])
        ]

        evidence_refs = self._build_evidence_refs(
            symptoms=symptoms,
            tongue_tags=tongue_tags,
            pulse_tags=pulse_tags,
            top_candidates=[item["syndrome"] for item in candidates[:3]],
        )

        low_confidence = top_score < 5.0
        if top_candidate and not low_confidence:
            formula_result = reasoning_service.reason_formula(
                syndrome=top_candidate["syndrome"],
                contraindications=self._extract_contraindications(input_summary.get("past_history", "")),
                patient_profile={"age": patient.get("age")},
            )
            formula_draft = {
                "principle": formula_result["therapy_principle"],
                "formula": formula_result["base_formula"],
                "modifications": formula_result.get("modifications", [])[:4],
                "note": "当前为辅助草案，需医生结合病情确认。",
            }
        else:
            formula_draft = {
                "principle": "当前信息不足，暂不建议直接给出固定治法。",
                "formula": "待补齐舌脉、病程与伴随症状后生成",
                "modifications": [
                    "优先补充口干是否欲饮、喜冷喜热、二便、睡眠时长等关键鉴别信息。"
                ],
                "note": "低置信度阶段仅保留候选证型与追问方向。",
            }

        structured_features = {
            "main_symptoms": symptoms,
            "tongue_features": tongue_tags,
            "pulse_features": pulse_tags,
            "heat_sign": self._has_heat_sign(symptoms, tongue_tags, pulse_tags),
            "phlegm_sign": self._has_phlegm_sign(symptoms, tongue_tags, pulse_tags),
            "disease_location": self._infer_disease_location(symptoms),
            "disease_nature": self._infer_disease_nature(symptoms, tongue_tags, pulse_tags),
        }

        risk_alerts = self._build_risk_alerts(
            intake=intake,
            input_summary=input_summary,
            top_syndromes=top_syndromes,
            low_confidence=low_confidence,
        )

        doctor_defaults = {
            "final_syndrome": top_syndromes[0]["name"] if top_syndromes else "待确认",
            "final_therapy": formula_draft["principle"],
            "final_formula": formula_draft["formula"],
            "adopt_ai": True,
        }

        return {
            "case_id": case_id,
            "patient_id": patient["patient_id"],
            "patient_card": patient,
            "input_summary": input_summary,
            "structured_features": structured_features,
            "top_syndromes": top_syndromes,
            "rule_hits": rule_hits,
            "evidence_refs": evidence_refs,
            "formula_draft": formula_draft,
            "risk_alerts": risk_alerts,
            "trace_steps": trace.get("steps", []),
            "doctor_defaults": doctor_defaults,
        }

    def commit(self, payload: Dict[str, Any], actor: str = "doctor") -> Dict[str, Any]:
        case_id = str(payload.get("case_id") or "demo-case")
        patient_info = {
            "name": payload.get("patient_name") or "匿名患者",
            "gender": payload.get("gender") or "未填写",
            "age": payload.get("age") or "未填写",
        }
        visit_data = {
            "chief_complaint": payload.get("chief_complaint") or "未填写",
            "history": payload.get("present_illness") or payload.get("doctor_notes") or "未填写",
            "tongue": payload.get("tongue") or "未填写",
            "pulse": payload.get("pulse") or "未填写",
        }
        reasoning_result = {
            "syndrome": payload.get("final_syndrome") or "待确认",
            "therapy": payload.get("final_therapy") or "待确认",
            "formula": payload.get("final_formula") or "待确认",
            "explanation": payload.get("doctor_notes") or "医生已人工确认。",
        }
        draft = document_service.draft(
            template_type="clinical_note",
            patient_info=patient_info,
            visit_data=visit_data,
            reasoning_result=reasoning_result,
        )

        ai_top_syndrome = str(payload.get("ai_top_syndrome") or "").strip()
        final_syndrome = str(payload.get("final_syndrome") or "").strip()
        adopt_ai = bool(payload.get("adopt_ai", True))
        action = "accept" if adopt_ai and ai_top_syndrome and ai_top_syndrome == final_syndrome else "modify"
        if not final_syndrome:
            action = "reject"

        feedback_id = feedback_service.submit(
            {
                "case_id": case_id,
                "actor": actor,
                "action": action,
                "comments": payload.get("doctor_notes") or None,
                "patched_formula": payload.get("final_formula") or None,
            }
        )
        audit_item = record_event(
            event_type="clinical.demo_commit",
            actor=actor,
            details={
                "case_id": case_id,
                "patient_id": payload.get("patient_id"),
                "adopt_ai": adopt_ai,
                "ai_top_syndrome": ai_top_syndrome,
                "final_syndrome": final_syndrome,
            },
        )
        return {
            "status": "saved",
            "case_id": case_id,
            "feedback_id": feedback_id,
            "audit_id": audit_item["event_id"],
            "writeback_message": "已生成病历草稿、提交反馈样本并写入审计记录。",
            "draft": draft,
            "action": action,
        }

    def _build_patient_card(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "case_id": str(payload.get("case_id") or "demo-case"),
            "patient_id": str(payload.get("patient_id") or "P-DEMO"),
            "name": str(payload.get("name") or "匿名患者"),
            "gender": str(payload.get("gender") or "未填写"),
            "age": payload.get("age") or "未填写",
            "department": str(payload.get("department") or "中医内科"),
            "visit_type": str(payload.get("visit_type") or "初诊"),
            "visit_time": str(payload.get("visit_time") or "待填写"),
        }

    def _build_input_summary(self, payload: Dict[str, Any]) -> Dict[str, str]:
        symptom_text = "、".join(payload.get("symptoms") or [])
        return {
            "chief_complaint": str(payload.get("chief_complaint") or "").strip(),
            "present_illness": str(payload.get("present_illness") or symptom_text).strip(),
            "tongue": str(payload.get("tongue") or "").strip(),
            "pulse": str(payload.get("pulse") or "").strip(),
            "exam_results": str(payload.get("exam_results") or "").strip(),
            "past_history": str(payload.get("past_history") or "").strip(),
        }

    def _collect_symptoms(self, payload: Dict[str, Any], intake: Dict[str, Any]) -> List[str]:
        text = " ".join(
            [
                str(payload.get("chief_complaint") or ""),
                str(payload.get("present_illness") or ""),
                " ".join(payload.get("symptoms") or []),
                str(payload.get("exam_results") or ""),
            ]
        )
        known_terms = sorted({term for rule in SYNDROME_RULES.values() for term in rule.get("symptoms", [])}, key=len, reverse=True)
        symptoms = list(dict.fromkeys((payload.get("symptoms") or []) + intake.get("standardized_fields", {}).get("symptoms", [])))
        for term in known_terms:
            if term in text and term not in symptoms:
                symptoms.append(term)
        return symptoms[:10]

    def _collect_tags(self, text: str, known_tags: List[str]) -> List[str]:
        normalized_text = re.sub(r"[，,、；;]\s*", " ", text or "")
        tags = [term for term in known_tags if term and term in normalized_text]
        return list(dict.fromkeys(tags))[:6]

    def _all_tongue_tags(self) -> List[str]:
        return sorted({tag for rule in SYNDROME_RULES.values() for tag in rule.get("tongue_tags", [])}, key=len, reverse=True)

    def _all_pulse_tags(self) -> List[str]:
        return sorted({tag for rule in SYNDROME_RULES.values() for tag in rule.get("pulse_tags", [])}, key=len, reverse=True)

    def _normalize_score(self, score: float) -> float:
        return round(min(0.98, 0.12 + max(score, 0) / 15.0), 2)

    def _clean_rule_item(self, value: str) -> str:
        text = str(value or "")
        if ":" in text:
            return text.split(":", 1)[1].strip()
        return text.strip()

    def _build_evidence_refs(
        self,
        symptoms: List[str],
        tongue_tags: List[str],
        pulse_tags: List[str],
        top_candidates: List[str],
    ) -> List[Dict[str, Any]]:
        query_terms = symptoms[:4] + tongue_tags[:2] + pulse_tags[:2] + top_candidates[:2]
        query = " ".join([item for item in query_terms if item]).strip()
        if not query:
            return []

        refs: List[Dict[str, Any]] = []
        for hit in professional_knowledge_service.search(query=query, top_k=4):
            matched_terms = [term for term in query_terms if term and (term in hit.get("title", "") or term in hit.get("snippet", ""))]
            if not matched_terms:
                continue
            refs.append(
                {
                    "source": hit.get("title"),
                    "support_point": "支持点：" + "、".join(list(dict.fromkeys(matched_terms))[:4]),
                    "quote": hit.get("snippet", "")[:96],
                }
            )
        if refs:
            return refs[:3]

        for hit in knowledge_service.search(query=query, top_k=3):
            matched_terms = [term for term in query_terms if term and (term in hit.get("title", "") or term in hit.get("snippet", ""))]
            if not matched_terms:
                continue
            refs.append(
                {
                    "source": hit.get("title"),
                    "support_point": "支持点：" + "、".join(list(dict.fromkeys(matched_terms))[:4]),
                    "quote": hit.get("snippet", "")[:96],
                }
            )
        return refs[:3]

    def _extract_contraindications(self, past_history: str) -> List[str]:
        items: List[str] = []
        for term in ["妊娠", "孕", "糖尿病", "免疫抑制", "老年"]:
            if term in past_history:
                items.append(term)
        return items

    def _has_heat_sign(self, symptoms: List[str], tongue_tags: List[str], pulse_tags: List[str]) -> bool:
        text = " ".join(symptoms + tongue_tags + pulse_tags)
        return any(term in text for term in ["口干", "口苦", "心烦", "舌红", "苔黄", "脉数", "低热"])

    def _has_phlegm_sign(self, symptoms: List[str], tongue_tags: List[str], pulse_tags: List[str]) -> bool:
        text = " ".join(symptoms + tongue_tags + pulse_tags)
        return any(term in text for term in ["痰多", "胸闷", "苔腻", "苔白腻", "苔黄腻", "脉滑"])

    def _infer_disease_location(self, symptoms: List[str]) -> List[str]:
        mapping = {
            "心": {"失眠", "心烦", "心悸"},
            "肝": {"口苦", "心烦", "头晕"},
            "脾": {"纳差", "腹胀", "便溏", "乏力"},
            "肺": {"咳嗽", "痰多", "气短", "胸闷"},
            "胃": {"口干", "纳差", "腹胀"},
        }
        result: List[str] = []
        symptom_set = set(symptoms)
        for organ, terms in mapping.items():
            if symptom_set & terms:
                result.append(organ)
        return result[:3] or ["待综合判断"]

    def _infer_disease_nature(self, symptoms: List[str], tongue_tags: List[str], pulse_tags: List[str]) -> List[str]:
        nature: List[str] = []
        merged = " ".join(symptoms + tongue_tags + pulse_tags)
        if self._has_heat_sign(symptoms, tongue_tags, pulse_tags):
            nature.append("热")
        if self._has_phlegm_sign(symptoms, tongue_tags, pulse_tags):
            nature.append("痰")
        if any(term in merged for term in ["乏力", "便溏", "脉弱", "舌淡"]):
            nature.append("虚")
        if any(term in merged for term in ["舌暗", "脉涩", "胸痛"]):
            nature.append("瘀")
        return nature[:4] or ["待判断"]

    def _build_risk_alerts(
        self,
        intake: Dict[str, Any],
        input_summary: Dict[str, str],
        top_syndromes: List[Dict[str, Any]],
        low_confidence: bool,
    ) -> List[str]:
        alerts: List[str] = []
        missing_fields = intake.get("missing_fields", []) or []
        if missing_fields:
            field_map = {
                "chief_complaint": "主诉",
                "duration": "病程",
                "tongue": "舌象",
                "pulse": "脉象",
                "sleep": "睡眠情况",
                "stool_urine": "二便情况",
            }
            display_missing = [field_map.get(item, item) for item in missing_fields[:4]]
            alerts.append("当前仍缺少关键信息：" + "、".join(display_missing))
        red_flags = intake.get("red_flags", []) or []
        if red_flags:
            alerts.append("已触发红旗症状：" + "、".join(red_flags) + "，建议优先线下评估。")
        if low_confidence:
            alerts.append("当前证候排序置信度不足，建议继续补充病程、睡眠、二便及舌脉信息后再判断。")
        if any(term in input_summary.get("past_history", "") for term in ["孕", "妊娠"]):
            alerts.append("涉及妊娠相关风险，方药建议必须由线下医生确认。")
        if top_syndromes:
            alerts.append("当前结果仅作临床辅助参考，不替代执业医师面诊。")
        return alerts[:4]


clinical_service = ClinicalService()
