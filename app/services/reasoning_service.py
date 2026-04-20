from __future__ import annotations

from typing import Any, Dict, List

from app.core.config import SYNDROME_RULES
from app.services.professional_knowledge_service import professional_knowledge_service


class ReasoningService:
    def reason_syndrome(
        self,
        symptoms: List[str],
        tongue_tags: List[str],
        pulse_tags: List[str],
        constraints: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        candidates = []
        feature_text = " ".join(symptoms + tongue_tags + pulse_tags)

        symptom_set = set(symptoms)
        tongue_set = set(tongue_tags)
        pulse_set = set(pulse_tags)

        for syndrome, rule in SYNDROME_RULES.items():
            score = 0.0
            support_evidence: List[str] = []
            counter_evidence: List[str] = []

            for item in rule["symptoms"]:
                if item in symptom_set:
                    score += 2.0
                    support_evidence.append(f"症状匹配: {item}")
                else:
                    if len(counter_evidence) < 2:
                        counter_evidence.append(f"缺少典型症状: {item}")

            for item in rule["tongue_tags"]:
                if item in tongue_set:
                    score += 1.5
                    support_evidence.append(f"舌象匹配: {item}")

            for item in rule["pulse_tags"]:
                if item in pulse_set:
                    score += 1.0
                    support_evidence.append(f"脉象匹配: {item}")

            if constraints.get("pregnant") and "活血" in rule["therapy"]:
                score -= 1.5
                counter_evidence.append("孕期需谨慎使用活血法")

            # 引入专业中医数据库证据，提升推理可追溯性
            professional_hits = professional_knowledge_service.search(
                query=f"{syndrome} {feature_text}".strip(),
                top_k=1,
            )
            if professional_hits:
                hit = professional_hits[0]
                snippet = hit["snippet"][:64]
                if len(hit["snippet"]) > 64:
                    snippet += "..."
                support_evidence.append(
                    f"专业库证据: {hit['title']} | {snippet} ({hit['source_path']})"
                )
                score += 0.8

            explanation = (
                f"该证候与输入信息存在 {len(support_evidence)} 项关键匹配，"
                f"当前治法建议为“{rule['therapy']}”。"
            )

            candidates.append(
                {
                    "syndrome": syndrome,
                    "score": round(score, 3),
                    "support_evidence": support_evidence,
                    "counter_evidence": counter_evidence,
                    "explanation": explanation,
                }
            )

        candidates.sort(key=lambda x: x["score"], reverse=True)
        return candidates[:3]

    def reason_trace(
        self,
        symptoms: List[str],
        tongue_tags: List[str],
        pulse_tags: List[str],
        constraints: Dict[str, Any],
    ) -> Dict[str, Any]:
        feature_text = " ".join(symptoms + tongue_tags + pulse_tags)
        all_candidates = self.reason_syndrome(
            symptoms=symptoms,
            tongue_tags=tongue_tags,
            pulse_tags=pulse_tags,
            constraints=constraints,
        )
        candidates = all_candidates[:1]
        excluded = all_candidates[1:]

        rule_scores = []
        for item in candidates:
            rule_scores.append(
                {
                    "syndrome": item["syndrome"],
                    "score": item["score"],
                    "support_count": len(item.get("support_evidence", [])),
                    "counter_count": len(item.get("counter_evidence", [])),
                }
            )

        retrieval_hits = professional_knowledge_service.search(
            query=feature_text,
            top_k=5,
        )

        return {
            "steps": [
                {
                    "name": "输入标准化",
                    "status": "done",
                    "detail": {
                        "symptoms": symptoms,
                        "tongue_tags": tongue_tags,
                        "pulse_tags": pulse_tags,
                        "constraints": constraints,
                    },
                },
                {
                    "name": "候选检索",
                    "status": "done",
                    "detail": [
                        {
                            "title": hit["title"],
                            "source_type": hit["source_type"],
                            "source_path": hit.get("source_path"),
                            "snippet": hit["snippet"],
                            "score": hit["score"],
                        }
                        for hit in retrieval_hits
                    ],
                },
                {
                    "name": "规则打分",
                    "status": "done",
                    "detail": rule_scores,
                },
                {
                    "name": "模型重排",
                    "status": "done",
                    "detail": [
                        {
                            "rank": idx + 1,
                            "syndrome": item["syndrome"],
                            "score": item["score"],
                            "explanation": item["explanation"],
                        }
                        for idx, item in enumerate(all_candidates)
                    ],
                },
                {
                    "name": "候选排除说明",
                    "status": "done",
                    "detail": [
                        {
                            "syndrome": item["syndrome"],
                            "exclude_reason": (
                                item.get("counter_evidence", ["综合评分低于当前主证候"])[0]
                            ),
                            "score": item["score"],
                        }
                        for item in excluded
                    ],
                },
                {
                    "name": "人工确认",
                    "status": "required",
                    "detail": {
                        "message": "必须由临床医生确认后，方可进入文书与处方流程。",
                        "checklist": [
                            "确认核心主诉和舌脉特征是否与候选证候一致",
                            "确认是否存在禁忌（孕期、肝肾功能、合并用药）",
                            "确认方药草案可执行并允许进入病历生成",
                        ],
                    },
                },
            ],
            "top_candidate": candidates[0] if candidates else None,
            "excluded_candidates": excluded,
        }

    def reason_formula(self, syndrome: str, contraindications: List[str], patient_profile: Dict[str, Any]) -> Dict[str, Any]:
        rule = SYNDROME_RULES.get(syndrome)
        if not rule:
            return {
                "therapy_principle": "请先明确证候后再给出处方草案",
                "base_formula": "待定",
                "modifications": ["建议补充四诊证据后重试"],
                "cautions": ["自动草案不可替代医生处方"],
            }

        cautions = ["本结果为辅助建议，需由执业医生最终确认。"]
        professional_hits = professional_knowledge_service.search(
            query=f"{syndrome} {rule['formula']} 治法 方药",
            top_k=2,
        )

        modifications = list(rule["mods"])
        if professional_hits:
            for hit in professional_hits:
                modifications.append(
                    f"专业库参考: {hit['title']}（{hit['source_path']}）"
                )

        for c in contraindications:
            cautions.append(f"禁忌提醒: {c}")

        age = patient_profile.get("age")
        if isinstance(age, int) and age >= 65:
            cautions.append("老年患者需关注肝肾功能与药物相互作用。")

        return {
            "therapy_principle": rule["therapy"],
            "base_formula": rule["formula"],
            "modifications": modifications,
            "cautions": cautions,
        }


reasoning_service = ReasoningService()
