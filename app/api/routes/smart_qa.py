from __future__ import annotations

from typing import Any, Dict, Tuple
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request

from app.api.routes.utils import resolve_actor
from app.core.audit import record_event
from app.models.schemas import (
    SmartQARequest,
    SmartQAResponse,
    SmartQATaskExecuteRequest,
    SmartQATaskExecuteResponse,
)
from app.services.document_service import document_service
from app.services.review_service import review_service
from app.services.smart_qa_service import smart_qa_service

router = APIRouter(tags=["smart_qa"])


@router.get("/smart-qa/scenarios")
def smart_qa_scenarios() -> dict:
    return {
        "scenarios": smart_qa_service.list_scenarios(),
    }


@router.post("/smart-qa/ask", response_model=SmartQAResponse)
def smart_qa_ask(payload: SmartQARequest, request: Request) -> SmartQAResponse:
    result = smart_qa_service.ask(
        question=payload.question,
        mode=payload.mode,
        scenario=payload.scenario,
        attachments=[item.model_dump() for item in payload.attachments],
        history=payload.history,
    )

    record_event(
        event_type="smart_qa.ask",
        actor=resolve_actor(request, default="visitor"),
        details={
            "mode": payload.mode,
            "scenario": result.get("scenario", ""),
            "risk_level": result.get("risk_level", "safe"),
            "attachment_count": len(payload.attachments),
            "question_length": len(payload.question or ""),
        },
    )

    return SmartQAResponse(**result)


def _build_document_context(payload: SmartQATaskExecuteRequest) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    result_cards = payload.result_cards or {}
    extracted_fields = payload.extracted_fields or {}

    syndrome_candidates = result_cards.get("syndrome_candidates", [])
    top_syndrome = syndrome_candidates[0].get("name") if syndrome_candidates else "待确认"
    therapy = (result_cards.get("therapy_suggestions") or ["待确认"])[0]
    formula = (result_cards.get("formula_draft") or {}).get("name", "待确认")

    evidence_titles = []
    for item in payload.evidences[:3]:
        title = str(item.get("title", "")).strip()
        source_type = str(item.get("source_type", "")).strip()
        if title:
            evidence_titles.append(f"[{source_type}] {title}" if source_type else title)

    patient_info = {
        "name": "匿名用户",
        "gender": "未填写",
        "age": "未填写",
    }
    visit_data = {
        "chief_complaint": result_cards.get("chief_complaint_summary", payload.question or "未填写"),
        "history": payload.question or "未填写",
        "tongue": "、".join(extracted_fields.get("tongue_tags", [])) or "未填写",
        "pulse": "、".join(extracted_fields.get("pulse_tags", [])) or "未填写",
        "question": payload.question or "未填写",
    }
    reasoning_result = {
        "syndrome": top_syndrome,
        "therapy": therapy,
        "formula": formula,
        "explanation": "；".join(result_cards.get("risk_prompts", [])[:2]) or "待补充",
        "evidence": "；".join(evidence_titles) if evidence_titles else "待补充",
        "hypothesis": f"基于证候“{top_syndrome}”进一步补齐四诊信息后复核。",
    }
    return patient_info, visit_data, reasoning_result


@router.post("/smart-qa/task-execute", response_model=SmartQATaskExecuteResponse)
def smart_qa_task_execute(payload: SmartQATaskExecuteRequest, request: Request) -> SmartQATaskExecuteResponse:
    action = payload.action.strip().lower()
    actor = resolve_actor(request, default="doctor")
    case_id = payload.case_id or f"qa-{uuid4().hex[:8]}"

    if action not in {
        "generate_summary",
        "generate_report",
        "expert_review",
        "save_case",
        "export_followup",
        "push_research",
        "fill_missing_fields",
        "open_intake_checklist",
        "start_imaging_review",
        "upload_materials",
    }:
        raise HTTPException(status_code=400, detail="invalid_action")

    patient_info, visit_data, reasoning_result = _build_document_context(payload)

    message = "任务执行完成"
    draft = None
    task_status = "done"
    review_task: Dict[str, Any] = {}
    extra_payload: Dict[str, Any] = {}

    if action == "generate_summary":
        draft = document_service.draft(
            template_type="clinical_note",
            patient_info=patient_info,
            visit_data=visit_data,
            reasoning_result=reasoning_result,
        )
        message = "已生成病历摘要草稿"

    elif action == "generate_report":
        draft = document_service.draft(
            template_type="research_summary",
            patient_info=patient_info,
            visit_data=visit_data,
            reasoning_result=reasoning_result,
        )
        message = "已生成辨证报告草稿"

    elif action == "expert_review":
        review_task = review_service.create_task(
            task_type="case",
            priority="high",
            title=f"智慧问答复核：{payload.scenario or '通用场景'}",
            summary=(payload.question[:120] if payload.question else "用户触发专家复核"),
            ai_prejudge=f"建议证候：{reasoning_result.get('syndrome', '待确认')}",
            evidence_refs=[item.get("object_id", "") for item in payload.evidences[:4] if item.get("object_id")],
        )
        message = "已创建专家复核任务"
        extra_payload = {"review_task_id": review_task.get("task_id")}

    elif action == "start_imaging_review":
        review_task = review_service.create_task(
            task_type="risk",
            priority="high",
            title="检查与证据复核任务",
            summary=(payload.comment or "根据智慧问答结果发起证据复核"),
            ai_prejudge="建议补齐舌象/脉象/关键检验信息后复核。",
            evidence_refs=["qa://smart-qa", f"case://{case_id}"],
        )
        message = "已发起检查与证据复核任务"
        extra_payload = {"review_task_id": review_task.get("task_id")}

    elif action == "save_case":
        record_event(
            event_type="feedback.loop_action",
            actor=actor,
            details={
                "case_id": case_id,
                "action": "add_teaching_case",
                "comment": payload.comment or "来自智慧问答任务面板",
            },
        )
        message = "已沉淀到病例库/教学案例池"

    elif action == "export_followup":
        draft = "\n".join(
            [
                "【随访计划草案】",
                "1. 48小时内补齐舌象、脉象与关键检查结果。",
                "2. 3-7天内完成复诊复核，校正证候与治法。",
                "3. 若症状加重或出现高风险信号，立即线下就医。",
            ]
        )
        message = "已生成随访计划"

    elif action == "push_research":
        draft = "\n".join(
            [
                "【科研项目夹推送草案】",
                f"- 研究问题：{visit_data.get('question', '未填写')}",
                f"- 关键证候：{reasoning_result.get('syndrome', '待确认')}",
                f"- 证据提要：{reasoning_result.get('evidence', '待补充')}",
                "- 后续动作：扩展样本、补齐反例、进行规则一致性验证。",
            ]
        )
        message = "已推送科研草稿"

    elif action == "fill_missing_fields":
        missing_items = payload.extracted_fields.get("missing_items", [])
        task_status = "pending"
        message = (
            "请补齐关键信息："
            + ("、".join(missing_items) if missing_items else "舌象、脉象、病程、检查结果")
        )
        extra_payload = {"missing_items": missing_items}

    elif action == "open_intake_checklist":
        draft = "\n".join(
            [
                "【四诊采集清单】",
                "1. 主诉与持续时间：何时开始、是否加重、诱因与缓解因素。",
                "2. 伴随症状：睡眠、饮食、二便、寒热、情志、疼痛部位与性质。",
                "3. 舌象与脉象：舌质、舌苔、脉象特征，可补充照片或门诊记录。",
                "4. 检查资料：化验、影像、既往病历、既往用药与疗效反馈。",
            ]
        )
        task_status = "pending"
        message = "已生成四诊采集清单，请补齐后再次发起分析"

    elif action == "upload_materials":
        task_status = "pending"
        message = "请补充上传舌象、病历或检查材料后再次发起分析"
        extra_payload = {
            "accepted_file_types": ["image", "document", "audio"],
            "recommended_materials": ["舌象照片", "门诊病历", "化验或影像结果"],
        }

    record_event(
        event_type="smart_qa.task_execute",
        actor=actor,
        details={
            "action": action,
            "case_id": case_id,
            "scenario": payload.scenario or "",
            "has_draft": bool(draft),
            "review_task_id": review_task.get("task_id"),
            "task_status": task_status,
        },
    )

    return SmartQATaskExecuteResponse(
        status="ok",
        action=action,
        message=message,
        task_status=task_status,
        draft=draft,
        review_task=review_task,
        payload=extra_payload,
    )
