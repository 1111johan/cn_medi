from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from app.core.config import SELF_MODEL_NAME, SYNDROME_RULES
from app.services.knowledge_service import knowledge_service
from app.services.llm_gateway_service import llm_gateway_service
from app.services.professional_knowledge_service import professional_knowledge_service

BOUNDARY_KEYWORDS = {
    "确诊",
    "诊断",
    "开药",
    "处方",
    "剂量",
    "用药方案",
    "我是不是",
    "能不能确诊",
    "替我判断",
    "给我配药",
    "直接开方",
    "按这个吃药",
}

OUT_OF_SCOPE_TERMS = {"股票", "币圈", "彩票", "代码报错", "旅游签证", "合同纠纷"}

GENERAL_GUIDE_TERMS = {
    "如何",
    "怎么",
    "怎样",
    "是什么",
    "原理",
    "流程",
    "步骤",
    "方法",
    "思路",
    "基础",
    "入门",
    "判断",
    "辨别",
    "区分",
}

PATIENT_CASE_HINT_TERMS = {
    "我",
    "本人",
    "最近",
    "这几天",
    "一直",
    "已经",
    "出现",
    "伴有",
    "加重",
    "缓解",
    "主诉",
    "病史",
    "复诊",
    "检查",
    "化验",
    "结果",
}

FAQ_LIBRARY = [
    {
        "keywords": ["四诊", "望闻问切", "辨证"],
        "min_match": 1,
        "answer": "中医辨证建议先补齐四诊信息（望闻问切），再结合病程与体质判断证候与治法。",
    },
    {
        "keywords": ["舌象", "脉象", "证候", "治法", "方药"],
        "min_match": 2,
        "answer": "当前问答可先给出证候候选与治法思路，最终处置请由线下医生结合舌脉与检查结果确认。",
    },
    {
        "keywords": ["古籍", "出处", "原文", "条文"],
        "min_match": 1,
        "answer": "可进入“科研传承”模式检索古籍条文、现代指南和医案证据，并按引用格式导出。",
    },
]

SCENARIO_GUIDES: Dict[str, Dict[str, Any]] = {
    "临床辨证": {
        "keywords": ["症状", "主诉", "辨证", "舌", "脉", "方药"],
        "steps": [
            "先归纳主诉、病程与伴随症状，形成结构化四诊要点。",
            "结合舌脉信息完成证候候选排序，输出支持证据与反证。",
            "生成治法与方药草案，并提示缺失项与风险边界。",
            "必要时发起专家复核，完成采纳/修改/驳回闭环。",
        ],
        "route": ["临床智能工作站", "专家复核中心", "病历与随访流程"],
        "prompts": [
            "帮我做中医辨证分析",
            "根据舌象判断证型",
            "给出治法和方药思路",
        ],
    },
    "科研传承": {
        "keywords": ["科研", "文献", "古籍", "医案", "综述", "课题"],
        "steps": [
            "明确研究问题并圈定证据范围（古籍/医案/指南/论文）。",
            "返回可引用证据片段，标注来源与关联对象。",
            "输出结构化研究摘要并推送到课题项目夹。",
        ],
        "route": ["科研传承工作台", "知识图谱关系视图", "研究导出与审阅"],
        "prompts": [
            "查找相关古籍依据",
            "汇总同证候的现代研究",
            "把本次结果导出为研究摘要",
        ],
    },
    "方药解析": {
        "keywords": ["方剂", "配伍", "药材", "归经", "加减", "药效"],
        "steps": [
            "识别方药对象与目标证候，提取核心药味与配伍关系。",
            "输出治法一致性、加减建议与禁忌提醒。",
            "形成研发或临床讨论草案，进入专家审核流程。",
        ],
        "route": ["中药研发工作台", "推理中台", "专家审核中心"],
        "prompts": [
            "解释这个方剂的组方思路",
            "分析药材归经与配伍关系",
            "输出风险禁忌与复核建议",
        ],
    },
    "体质调理": {
        "keywords": ["体质", "调理", "虚实", "寒热", "气血", "阴阳"],
        "steps": [
            "归纳体质倾向与主要不适，识别寒热虚实与气血津液状态。",
            "给出饮食起居、情志调摄与阶段性调理建议。",
            "按复诊反馈动态校正证候优先级与调理策略。",
        ],
        "route": ["临床智能工作站", "随访管理窗口", "专家复核中心"],
        "prompts": [
            "请判断我偏哪种体质并给出调理建议",
            "最近总是疲倦乏力，如何做中医调理？",
            "饮食和作息应如何配合当前体质？",
        ],
    },
    "慢病调护": {
        "keywords": ["慢病", "复诊", "管理", "调护", "随访", "长期"],
        "steps": [
            "整合既往病史、近期症状与复诊指标，明确当前阶段目标。",
            "输出阶段性治法、方药思路与风险提醒。",
            "生成随访计划并沉淀为可复用病例样本。",
        ],
        "route": ["慢病管理工作台", "专家审核中心", "随访流程"],
        "prompts": [
            "慢病复诊时需要重点补充哪些信息？",
            "如何做分阶段的中医调护方案？",
            "请帮我生成下次复诊随访计划",
        ],
    },
    "服药不良反应": {
        "keywords": ["服药", "不良反应", "副作用", "恶心", "皮疹"],
        "steps": [
            "记录出现时间、症状表现与当前用药名称。",
            "尽快联系随访医生，不建议自行停药或加减药。",
            "必要时补做肝肾功能、血常规等安全性检查。",
        ],
        "route": ["随访管理窗口", "专科门诊", "急诊（重度不适）"],
        "prompts": [
            "服药后恶心和乏力怎么处理？",
            "哪些不良反应需要立即就医？",
            "可以自行停药吗？",
        ],
    },
}

DEFAULT_STEPS = [
    "先整理主要症状与持续时间，形成清晰问题描述。",
    "补充舌脉与检查结果，提升辨证与推理准确度。",
    "若触发高风险边界，优先走线下就医与复核流程。",
]

DEFAULT_PROMPTS = [
    "帮我做中医辨证分析",
    "根据舌象判断证型",
    "解释这个方药思路",
    "查找相关古籍依据",
    "把问答整理成病历摘要",
    "生成随访计划",
]

SYMPTOM_TERMS = [
    "咳嗽",
    "咳痰",
    "痰多",
    "盗汗",
    "低热",
    "胸闷",
    "乏力",
    "气短",
    "咯血",
    "消瘦",
    "口苦",
    "失眠",
    "多梦",
    "心烦",
    "纳差",
    "食欲差",
    "口干",
    "头晕",
    "腹胀",
    "便溏",
    "胸痛",
    "心悸",
]

TONGUE_TERMS = [
    "舌红",
    "舌淡",
    "舌暗",
    "舌胖",
    "舌胖大",
    "齿痕",
    "苔黄腻",
    "苔白腻",
    "苔薄",
    "苔腻",
]

PULSE_TERMS = [
    "脉滑",
    "脉细",
    "脉数",
    "脉濡",
    "脉弦",
    "脉涩",
    "脉弱",
    "脉细弱",
]

RISK_HISTORY_TERMS = ["糖尿病", "免疫抑制", "长期激素", "老年", "吸烟", "慢阻肺", "孕", "妊娠"]

SYNDROME_PROFILES: Dict[str, Dict[str, Any]] = {
    "痰热扰心": {
        "symptoms": ["失眠", "多梦", "心烦", "口苦", "痰多", "胸闷"],
        "tongue_tags": ["舌红", "苔黄腻"],
        "pulse_tags": ["脉滑", "脉数"],
        "therapy": "清热化痰，宁心安神",
        "formula": "温胆汤加减",
    },
    "肝郁化火": {
        "symptoms": ["心烦", "口苦", "失眠", "胸闷", "头晕"],
        "tongue_tags": ["舌红"],
        "pulse_tags": ["脉弦", "脉数"],
        "therapy": "疏肝清热，解郁安神",
        "formula": "丹栀逍遥散加减",
    },
    "心脾两虚": {
        "symptoms": ["失眠", "心悸", "乏力", "食欲差", "头晕"],
        "tongue_tags": ["舌淡", "苔薄"],
        "pulse_tags": ["脉细", "脉弱"],
        "therapy": "益气养血，健脾安神",
        "formula": "归脾汤加减",
    },
    "痰湿阻肺": {
        "symptoms": ["咳嗽", "咳痰", "痰多", "胸闷", "气短"],
        "tongue_tags": ["苔白腻", "苔腻", "舌胖"],
        "pulse_tags": ["脉滑"],
        "therapy": "化痰祛湿，宣肺理气",
        "formula": "二陈汤合三子养亲汤加减",
    },
    "阴虚内热": {
        "symptoms": ["盗汗", "低热", "咯血", "消瘦", "口干"],
        "tongue_tags": ["舌红"],
        "pulse_tags": ["脉细", "脉数"],
        "therapy": "滋阴清热，润肺止咳",
        "formula": "沙参麦冬汤加减",
    },
    "脾肺气虚": {
        "symptoms": ["乏力", "气短", "食欲差", "咳嗽"],
        "tongue_tags": ["舌淡", "苔薄"],
        "pulse_tags": ["脉弱", "脉濡"],
        "therapy": "补益脾肺，扶正固表",
        "formula": "补肺汤合参苓白术散加减",
    },
    "痰瘀互结": {
        "symptoms": ["胸闷", "痰多", "胸痛", "咳嗽"],
        "tongue_tags": ["舌暗", "苔腻"],
        "pulse_tags": ["脉涩", "脉滑"],
        "therapy": "化痰散结，活血通络",
        "formula": "二陈汤合血府逐瘀汤加减",
    },
}

# 与平台规则中心保持一致
for syndrome_name, cfg in SYNDROME_RULES.items():
    SYNDROME_PROFILES.setdefault(
        syndrome_name,
        {
            "symptoms": cfg.get("symptoms", []),
            "tongue_tags": cfg.get("tongue_tags", []),
            "pulse_tags": cfg.get("pulse_tags", []),
            "therapy": cfg.get("therapy", "待确认"),
            "formula": cfg.get("formula", "待确认"),
        },
    )


class SmartQAService:
    def list_scenarios(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": name,
                "keywords": config["keywords"],
                "steps": config["steps"],
                "route": config["route"],
                "prompts": config.get("prompts", []),
            }
            for name, config in SCENARIO_GUIDES.items()
        ]

    def ask(
        self,
        question: str,
        mode: str = "text",
        scenario: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        clean_question = self._normalize(question)
        attachments = attachments or []

        extracted_fields = self._extract_fields(clean_question, attachments)
        is_general_question = self._is_general_question(clean_question, extracted_fields)

        resolved_scenario = self._resolve_scenario(scenario=scenario, question=clean_question, mode=mode)
        if is_general_question and not scenario:
            resolved_scenario = "科研传承"

        scenario_cfg = SCENARIO_GUIDES.get(resolved_scenario, {})
        steps = scenario_cfg.get("steps", DEFAULT_STEPS)
        route = scenario_cfg.get("route", ["临床智能工作站", "专家复核中心"])
        suggested_questions = scenario_cfg.get("prompts", DEFAULT_PROMPTS)

        missing_items = [] if is_general_question else extracted_fields.get("missing_items", [])
        syndrome_candidates = [] if is_general_question else self._infer_syndrome_candidates(extracted_fields, resolved_scenario)

        top_candidate = syndrome_candidates[0] if syndrome_candidates else {"name": "待结合四诊信息", "score": 0.0}
        top_syndrome = top_candidate["name"]

        strategy = SYNDROME_PROFILES.get(top_syndrome, {})
        therapy = strategy.get("therapy", "建议补齐四诊信息后再确定治法")
        formula = strategy.get("formula", "待补齐资料后生成")
        if is_general_question:
            therapy = "当前为通识问答场景，需结合个体四诊信息后再进入证候治法判断。"
            formula = "通识问答不直接生成方药草案。"

        local_hits = knowledge_service.search(query=clean_question, top_k=4)
        professional_hits = [] if is_general_question else professional_knowledge_service.search(query=clean_question, top_k=4)
        evidences = self._filter_out_of_scope_evidences(self._merge_evidences(local_hits, professional_hits))
        if is_general_question:
            evidences = []

        faq_answer = self._match_faq(clean_question) if is_general_question else ""
        attachment_note = self._attachment_note(attachments)
        boundary = self._boundary_notice(clean_question)
        topic_guarded = self._contains_out_of_scope_topic(clean_question)
        extracted_fields["topic_guarded"] = topic_guarded
        risk_prompts = self._build_risk_prompts(boundary, extracted_fields)

        fallback_answer = (
            f"结合当前输入信息，系统优先考虑证候为“{top_syndrome}”（置信度 {top_candidate.get('score', 0):.2f}），"
            f"建议治法为“{therapy}”，方药可参考“{formula}”。"
        )
        llm_result: Dict[str, Any] = {"ok": False, "provider": "self", "model": SELF_MODEL_NAME, "error": "not_called"}

        if topic_guarded:
            answer = "当前平台仅提供通用中医辨证、方药与科研问答，请改用症状、舌象、脉象、体质或方药问题继续咨询。"
            llm_result = {"ok": False, "provider": "self", "model": SELF_MODEL_NAME, "error": "topic_guard"}
        elif is_general_question:
            llm_result = self._generate_general_llm_answer(
                question=clean_question,
                scenario=resolved_scenario,
                boundary=boundary,
            )
            if llm_result.get("ok"):
                answer = llm_result.get("content", "")
            elif faq_answer:
                answer = faq_answer
                if llm_result.get("error") in {"not_called", "", None}:
                    llm_result = {"ok": False, "provider": "self", "model": SELF_MODEL_NAME, "error": "faq_hit"}
            else:
                answer = self._build_general_answer(clean_question)
                if llm_result.get("error") in {"not_called", "", None}:
                    llm_result = {"ok": False, "provider": "self", "model": SELF_MODEL_NAME, "error": "general_guide"}
        else:
            llm_result = self._generate_llm_answer(
                question=clean_question,
                scenario=resolved_scenario,
                top_candidate=top_candidate,
                syndrome_candidates=syndrome_candidates,
                therapy=therapy,
                formula=formula,
                evidences=evidences,
                missing_items=missing_items,
                boundary=boundary,
            )
            answer = llm_result.get("content", "") if llm_result.get("ok") else fallback_answer

        concise_notes: List[str] = []
        if boundary["is_boundary"]:
            concise_notes.append("提示：当前问题涉及诊疗边界，请线下就医并由医生最终确认。")
        if missing_items and not is_general_question:
            concise_notes.append("需补充信息：" + "、".join(missing_items[:4]))
        if attachment_note:
            concise_notes.append("已接收上传材料。")

        if concise_notes:
            answer = answer.strip() + "\n\n" + "\n".join(concise_notes)

        citation_block = self._build_citation_block(evidences) if not is_general_question else ""
        if citation_block:
            answer = answer.strip() + "\n\n" + citation_block

        speech_text = self._build_speech_text(answer)

        process_cards = self._build_process_cards(
            mode=mode,
            attachments=attachments,
            evidence_count=len(evidences),
            citation_count=min(len(evidences), 3),
            top_syndrome=top_syndrome,
            boundary=boundary,
            missing_items=missing_items,
            llm_result=llm_result,
        )
        graph_links = [] if is_general_question else self._build_graph_links(extracted_fields, syndrome_candidates, therapy, formula)
        workflow_tasks = (
            self._build_general_tasks()
            if is_general_question
            else self._build_workflow_tasks(boundary, missing_items, resolved_scenario)
        )

        result_cards = {
            "chief_complaint_summary": self._summarize_complaint(clean_question),
            "recognized_symptoms": extracted_fields.get("symptoms", []),
            "tongue_pulse": {
                "tongue": extracted_fields.get("tongue_tags", []),
                "pulse": extracted_fields.get("pulse_tags", []),
            },
            "syndrome_candidates": syndrome_candidates,
            "therapy_suggestions": [] if is_general_question else [therapy],
            "formula_draft": {
                "name": formula if not is_general_question else "待个体化辨证后生成",
                "note": (
                    "通识问答场景不输出个体化方药，需补齐主诉、舌脉与病程后再推理。"
                    if is_general_question
                    else "MVP 草案，仅作学术与流程演示，需医生审核确认。"
                ),
            },
            "risk_prompts": risk_prompts,
        }

        session_tags = [
            resolved_scenario,
            SELF_MODEL_NAME,
            "智能问答",
            "多模态分析中" if attachments else "文本问答",
            "边界校验" if boundary["is_boundary"] else "常规科普",
        ]

        digital_state = "answering"
        if boundary["is_boundary"]:
            digital_state = "caution"
        elif missing_items:
            digital_state = "asking"

        return {
            "answer": answer,
            "speech_text": speech_text,
            "risk_level": "caution" if boundary["is_boundary"] else "safe",
            "boundary_notice": boundary["message"],
            "scenario": resolved_scenario,
            "model_name": SELF_MODEL_NAME,
            "steps": steps,
            "recommended_route": route,
            "evidences": evidences,
            "conversation_title": f"{resolved_scenario}会话",
            "session_tags": session_tags,
            "suggested_questions": suggested_questions,
            "process_cards": process_cards,
            "extracted_fields": extracted_fields,
            "result_cards": result_cards,
            "graph_links": graph_links,
            "workflow_tasks": workflow_tasks,
            "missing_items": missing_items,
            "digital_human": {
                "avatar": "doctor-ai-guide",
                "emotion": "serious" if boundary["is_boundary"] else "calm",
                "voice": "zh-CN-female",
                "mode": mode,
                "state": digital_state,
                "speak_ready": bool(speech_text),
            },
        }

    def _resolve_scenario(self, scenario: Optional[str], question: str, mode: str) -> str:
        if scenario and scenario in SCENARIO_GUIDES:
            return scenario

        mode_hint = mode.strip().lower()
        if mode_hint == "research":
            return "科研传承"
        if mode_hint == "document":
            return "方药解析"

        for name, cfg in SCENARIO_GUIDES.items():
            if any(k in question for k in cfg["keywords"]):
                return name

        return "临床辨证"

    def _is_general_question(self, question: str, extracted_fields: Dict[str, Any]) -> bool:
        q = (question or "").strip()
        if not q:
            return False

        structured_signal_count = int(extracted_fields.get("structured_signal_count", 0) or 0)
        if structured_signal_count > 0:
            return False

        general_hint = any(token in q for token in GENERAL_GUIDE_TERMS)
        case_hint = any(token in q for token in PATIENT_CASE_HINT_TERMS)
        explicit_method_pattern = bool(re.search(r"(如何|怎么|怎样).{0,8}(判断|辨别|区分|识别)", q))

        return (general_hint and not case_hint) or explicit_method_pattern

    def _build_general_answer(self, question: str) -> str:
        _ = question  # 保留参数，便于后续按问题定制模板
        return (
            "【初步判断】\n"
            "您当前属于中医通识方法咨询，不是个体病例辨证。中医判断症状核心是“四诊合参”，而不是单看一个症状。\n\n"
            "【原因说明】\n"
            "中医会综合主诉、伴随症状、病程变化、舌象、脉象与体质信息，再做证候归类。\n"
            "若缺少舌脉和病程信息，容易出现判断偏差。\n\n"
            "【下一步建议】\n"
            "1. 先记录主诉、持续时间、诱因与加重/缓解因素；\n"
            "2. 再补充舌象（舌质/苔）与脉象；\n"
            "3. 最后由执业中医师面诊完成辨证与治法确认。"
        )

    def _generate_general_llm_answer(
        self,
        question: str,
        scenario: str,
        boundary: Dict[str, Any],
    ) -> Dict[str, Any]:
        system_prompt = (
            "你是中医智能体平台的通识问答助手。"
            "请用中文输出，语气专业克制，不夸大、不替代医生。"
            "必须按三个小节输出：\n"
            "【初步判断】\n【原因说明】\n【下一步建议】"
        )
        user_prompt = (
            f"场景：{scenario}\n"
            f"用户问题：{question}\n"
            f"边界状态：{'触发边界' if boundary.get('is_boundary') else '常规科普'}\n"
            "要求：回答聚焦方法与步骤，不输出个体化诊断结论和具体处方剂量。"
        )
        return llm_gateway_service.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=420,
        )

    def _build_general_tasks(self) -> List[Dict[str, Any]]:
        return [
            {"title": "查看四诊采集清单", "action": "open_intake_checklist", "priority": "P1", "status": "ready"},
            {"title": "补充主诉与病程信息", "action": "fill_missing_fields", "priority": "P1", "status": "ready"},
            {"title": "上传舌象/病历材料", "action": "upload_materials", "priority": "P2", "status": "ready"},
        ]

    def _extract_fields(self, question: str, attachments: List[Dict[str, Any]]) -> Dict[str, Any]:
        symptoms = [item for item in SYMPTOM_TERMS if item in question]
        tongue_tags = [item for item in TONGUE_TERMS if item in question]
        pulse_tags = [item for item in PULSE_TERMS if item in question]
        risk_history = [item for item in RISK_HISTORY_TERMS if item in question]

        duration_match = re.search(r"(\d+\s*[天周月年])", question)
        duration = duration_match.group(1).replace(" ", "") if duration_match else ""

        has_exam = any(k in question for k in ["化验", "检验", "检查", "复诊", "病历", "体检", "指标"])
        check_status = "已提及检查" if has_exam else "检查信息缺失"

        attachment_summary = self._attachment_counts(attachments)

        missing_items: List[str] = []
        if not duration:
            missing_items.append("病程时长")
        if not tongue_tags:
            missing_items.append("舌象")
        if not pulse_tags:
            missing_items.append("脉象")
        if not has_exam:
            missing_items.append("检查结果")

        structured_signal_count = len(symptoms) + len(tongue_tags) + len(pulse_tags)
        if duration:
            structured_signal_count += 1
        if has_exam:
            structured_signal_count += 1

        return {
            "symptoms": symptoms,
            "tongue_tags": tongue_tags,
            "pulse_tags": pulse_tags,
            "risk_history": risk_history,
            "duration": duration,
            "has_exam": has_exam,
            "structured_signal_count": structured_signal_count,
            "check_status": check_status,
            "attachment_summary": attachment_summary,
            "missing_items": missing_items,
        }

    def _infer_syndrome_candidates(self, extracted_fields: Dict[str, Any], scenario: str) -> List[Dict[str, Any]]:
        symptoms = extracted_fields.get("symptoms", [])
        tongue_tags = extracted_fields.get("tongue_tags", [])
        pulse_tags = extracted_fields.get("pulse_tags", [])

        ranking: List[Dict[str, Any]] = []
        for syndrome_name, profile in SYNDROME_PROFILES.items():
            score = 0.18

            for item in symptoms:
                if item in profile.get("symptoms", []):
                    score += 0.12

            for item in tongue_tags:
                if item in profile.get("tongue_tags", []):
                    score += 0.14

            for item in pulse_tags:
                if item in profile.get("pulse_tags", []):
                    score += 0.13

            if scenario == "临床辨证" and syndrome_name in {"痰热扰心", "肝郁化火", "心脾两虚"}:
                score += 0.05
            if scenario == "方药解析" and syndrome_name in {"痰瘀互结", "痰湿阻肺"}:
                score += 0.05
            if scenario in {"体质调理", "慢病调护"} and syndrome_name in {"心脾两虚", "痰湿阻肺", "脾肺气虚"}:
                score += 0.06

            ranking.append({"name": syndrome_name, "score": round(min(0.98, score), 2)})

        ranking.sort(key=lambda x: x["score"], reverse=True)
        return ranking[:3]

    def _generate_llm_answer(
        self,
        question: str,
        scenario: str,
        top_candidate: Dict[str, Any],
        syndrome_candidates: List[Dict[str, Any]],
        therapy: str,
        formula: str,
        evidences: List[Dict[str, Any]],
        missing_items: List[str],
        boundary: Dict[str, Any],
    ) -> Dict[str, Any]:
        evidence_titles = [item.get("title", "") for item in evidences[:3] if item.get("title")]
        evidence_digest = self._build_evidence_digest(evidences)
        candidate_text = "、".join([f"{item['name']}({item['score']})" for item in syndrome_candidates[:3]]) or "暂无候选"

        system_prompt = (
            "你是中医智能体平台的问答助手。"
            "请用中文输出，语气专业克制。"
            "禁止输出确诊、处方剂量或替代医生面诊的结论。"
            "请严格按三个小节输出：\n"
            "【初步判断】\n【原因说明】\n【下一步建议】"
        )

        user_prompt = (
            f"场景：{scenario}\n"
            f"用户问题：{question}\n"
            f"候选证候：{candidate_text}\n"
            f"首位候选：{top_candidate.get('name', '待确认')}（置信度{top_candidate.get('score', 0)}）\n"
            f"建议治法：{therapy}\n"
            f"建议方药：{formula}\n"
            f"证据标题：{'；'.join(evidence_titles) if evidence_titles else '暂无'}\n"
            f"检索证据摘要：\n{evidence_digest}\n"
            f"缺失信息：{'、'.join(missing_items) if missing_items else '无'}\n"
            f"边界状态：{'触发边界' if boundary.get('is_boundary') else '常规科普'}\n"
            "要求：每个小节控制在3行以内；若触发边界，必须提示线下就医与医生确认；若有检索证据，"
            "在【原因说明】中尽量使用[1][2]的编号方式说明依据。"
        )

        return llm_gateway_service.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.25,
            max_tokens=600,
        )

    def _build_risk_prompts(self, boundary: Dict[str, Any], extracted_fields: Dict[str, Any]) -> List[str]:
        prompts: List[str] = []
        if boundary["is_boundary"]:
            prompts.append("当前问题触发诊断/处方边界，建议线下就医并由医生决策。")
        if extracted_fields.get("topic_guarded"):
            prompts.append("当前问题已按平台主题限制，返回通用中医建议。")

        missing_items = extracted_fields.get("missing_items", [])
        if missing_items:
            prompts.append("关键信息缺失：" + "、".join(missing_items))

        risk_history = extracted_fields.get("risk_history", [])
        if any(item in risk_history for item in {"孕", "妊娠"}):
            prompts.append("涉及妊娠相关风险，请务必由线下医生评估后决策。")

        if not prompts:
            prompts.append("当前为科普级低风险建议，仍需结合线下检查结果确认。")
        return prompts

    def _build_process_cards(
        self,
        mode: str,
        attachments: List[Dict[str, Any]],
        evidence_count: int,
        citation_count: int,
        top_syndrome: str,
        boundary: Dict[str, Any],
        missing_items: List[str],
        llm_result: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        cards = [
            {
                "stage": "输入解析",
                "status": "done",
                "message": f"已解析输入模式：{mode}",
            },
            {
                "stage": "多模态识别",
                "status": "done",
                "message": f"识别附件数量：{len(attachments)}",
            },
            {
                "stage": "知识检索",
                "status": "done",
                "message": f"命中可用证据 {evidence_count} 条",
            },
            {
                "stage": "检索引用分析",
                "status": "done" if citation_count > 0 else "watch",
                "message": (
                    f"已形成 {citation_count} 条可追溯引用"
                    if citation_count > 0
                    else "当前未命中高置信证据，建议补充症状/舌脉后重试"
                ),
            },
            {
                "stage": "大模型生成",
                "status": "done" if llm_result.get("ok") else "watch",
                "message": (
                    f"{SELF_MODEL_NAME} 已完成回答生成"
                    if llm_result.get("ok")
                    else f"{SELF_MODEL_NAME} 暂不可用，已回退规则回答（{llm_result.get('error', 'fallback')})"
                ),
            },
            {
                "stage": "神经符号融合评分",
                "status": "done",
                "message": f"当前首位证候：{top_syndrome}",
            },
            {
                "stage": "边界校验",
                "status": "warning" if boundary["is_boundary"] else "done",
                "message": boundary["message"],
            },
            {
                "stage": "结果沉淀",
                "status": "pending" if missing_items else "done",
                "message": "已生成结构化结果与任务建议" if not missing_items else "建议先补齐关键信息再进入报告生成",
            },
        ]
        return cards

    def _build_graph_links(
        self,
        extracted_fields: Dict[str, Any],
        syndrome_candidates: List[Dict[str, Any]],
        therapy: str,
        formula: str,
    ) -> List[Dict[str, Any]]:
        links: List[Dict[str, Any]] = []
        top_syndrome = syndrome_candidates[0]["name"] if syndrome_candidates else "待辨证"

        for symptom in extracted_fields.get("symptoms", [])[:5]:
            links.append(
                {
                    "source": symptom,
                    "target": top_syndrome,
                    "relation": "提示",
                }
            )

        for tag in extracted_fields.get("tongue_tags", [])[:2]:
            links.append(
                {
                    "source": tag,
                    "target": top_syndrome,
                    "relation": "舌象支持",
                }
            )

        for tag in extracted_fields.get("pulse_tags", [])[:2]:
            links.append(
                {
                    "source": tag,
                    "target": top_syndrome,
                    "relation": "脉象支持",
                }
            )

        links.append(
            {
                "source": top_syndrome,
                "target": therapy,
                "relation": "治法",
            }
        )
        links.append(
            {
                "source": therapy,
                "target": formula,
                "relation": "方药",
            }
        )

        return links[:12]

    def _build_workflow_tasks(
        self,
        boundary: Dict[str, Any],
        missing_items: List[str],
        scenario: str,
    ) -> List[Dict[str, Any]]:
        tasks = [
            {"title": "生成病历摘要", "action": "generate_summary", "priority": "P1", "status": "ready"},
            {"title": "生成辨证报告", "action": "generate_report", "priority": "P1", "status": "ready"},
            {"title": "加入病例库", "action": "save_case", "priority": "P2", "status": "ready"},
            {"title": "导出随访计划", "action": "export_followup", "priority": "P2", "status": "ready"},
            {"title": "推送科研项目夹", "action": "push_research", "priority": "P2", "status": "ready"},
        ]

        if boundary["is_boundary"]:
            tasks.insert(0, {"title": "发起专家复核", "action": "expert_review", "priority": "P0", "status": "urgent"})

        if missing_items:
            tasks.insert(
                1,
                {
                    "title": "补齐关键缺失项",
                    "action": "fill_missing_fields",
                    "priority": "P0",
                    "status": "pending",
                    "detail": "缺失：" + "、".join(missing_items),
                },
            )

        if scenario == "科研传承":
            tasks = [task for task in tasks if task["action"] not in {"generate_summary"}]

        return tasks[:7]

    def _summarize_complaint(self, question: str) -> str:
        if not question:
            return "未提供主诉"
        if len(question) <= 56:
            return question
        return question[:56] + "..."

    def _match_faq(self, question: str) -> str:
        for item in FAQ_LIBRARY:
            keywords = item.get("keywords", [])
            if not keywords:
                continue

            hit_count = sum(1 for k in keywords if k and k in question)
            min_match = int(item.get("min_match", 1))
            if hit_count >= max(1, min_match):
                return item["answer"]
        return ""

    def _attachment_note(self, attachments: List[Dict[str, Any]]) -> str:
        if not attachments:
            return ""

        groups = self._attachment_counts(attachments)
        names: List[str] = []
        for item in attachments:
            name = str(item.get("name", ""))
            if name:
                names.append(name)

        parts = [f"{k}:{v}个" for k, v in groups.items()]
        text = "已接收材料（" + "，".join(parts) + "）。"
        if names:
            text += "文件：" + "、".join(names[:4])
            if len(names) > 4:
                text += "等"
        text += "。本模块仅做初步科普解读，正式结论请以线下医疗机构检查为准。"
        return text

    def _attachment_counts(self, attachments: List[Dict[str, Any]]) -> Dict[str, int]:
        groups: Dict[str, int] = {}
        for item in attachments:
            file_type = str(item.get("file_type", "other"))
            groups[file_type] = groups.get(file_type, 0) + 1
        return groups

    def _boundary_notice(self, question: str) -> Dict[str, Any]:
        hit = any(word in question for word in BOUNDARY_KEYWORDS)
        if not hit:
            return {
                "is_boundary": False,
                "message": "当前问题可按健康科普边界回答。",
            }
        return {
            "is_boundary": True,
            "message": "检测到诊断/处方类问题，已触发边界控制。",
        }

    def _build_speech_text(self, answer: str) -> str:
        clean = re.sub(r"\s+", " ", answer).strip()
        if len(clean) <= 320:
            return clean
        return clean[:320] + "。完整内容请查看右侧文本。"

    def _build_evidence_digest(self, evidences: List[Dict[str, Any]]) -> str:
        if not evidences:
            return "暂无"
        lines: List[str] = []
        for idx, item in enumerate(evidences[:3], start=1):
            title = str(item.get("title", "")).strip() or "未命名证据"
            snippet = str(item.get("snippet", "")).strip()
            source_type = str(item.get("source_type", "")).strip()
            if len(snippet) > 72:
                snippet = snippet[:72] + "..."
            lines.append(f"[{idx}] {title} | {source_type} | {snippet}")
        return "\n".join(lines)

    def _build_citation_block(self, evidences: List[Dict[str, Any]]) -> str:
        if not evidences:
            return ""
        lines = ["【检索引用分析】"]
        for idx, item in enumerate(evidences[:3], start=1):
            title = str(item.get("title", "")).strip() or "未命名证据"
            source_type = str(item.get("source_type", "")).strip() or "unknown"
            snippet = str(item.get("snippet", "")).strip()
            if len(snippet) > 86:
                snippet = snippet[:86] + "..."
            lines.append(f"[{idx}] {title}（{source_type}）: {snippet}")
        lines.append("以上引用用于辅助推理，不替代执业医生面诊结论。")
        return "\n".join(lines)

    def _normalize(self, text: str) -> str:
        return re.sub(r"\s+", " ", text or "").strip()

    def _contains_out_of_scope_topic(self, text: str) -> bool:
        return any(token in text for token in OUT_OF_SCOPE_TERMS)

    def _filter_out_of_scope_evidences(self, evidences: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        clean_list: List[Dict[str, Any]] = []
        for item in evidences:
            merged_text = f"{item.get('title', '')} {item.get('snippet', '')}"
            if self._contains_out_of_scope_topic(merged_text):
                continue
            clean_list.append(item)
        return clean_list

    def _merge_evidences(self, local_hits: List[Dict[str, Any]], pro_hits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        merged: List[Dict[str, Any]] = []

        for item in local_hits:
            merged.append(
                {
                    "object_id": item["object_id"],
                    "title": item["title"],
                    "source_type": item["source_type"],
                    "snippet": item.get("snippet", "")[:180],
                    "score": float(item.get("score", 0)),
                }
            )

        for item in pro_hits:
            source_path = item.get("source_path", "")
            suffix = f" ({source_path})" if source_path else ""
            merged.append(
                {
                    "object_id": item["object_id"],
                    "title": f"{item['title']}{suffix}",
                    "source_type": item["source_type"],
                    "snippet": item.get("snippet", "")[:180],
                    "score": float(item.get("score", 0)),
                }
            )

        merged.sort(key=lambda x: x["score"], reverse=True)
        return merged[:8]


smart_qa_service = SmartQAService()
