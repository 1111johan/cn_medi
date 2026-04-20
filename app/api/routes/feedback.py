from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.api.routes.utils import resolve_actor
from app.core.audit import record_event
from app.models.schemas import FeedbackSubmitRequest, FeedbackSubmitResponse, LoopActionRequest
from app.services.feedback_service import feedback_service

router = APIRouter(tags=["feedback"])


@router.post("/feedback/submit", response_model=FeedbackSubmitResponse)
def submit_feedback(payload: FeedbackSubmitRequest, request: Request) -> FeedbackSubmitResponse:
    feedback_id = feedback_service.submit(payload.model_dump())
    record_event(
        event_type="feedback.submit",
        actor=resolve_actor(request, default=payload.actor),
        details={"feedback_id": feedback_id, "action": payload.action, "case_id": payload.case_id},
    )
    return FeedbackSubmitResponse(feedback_id=feedback_id, status="saved")


@router.post("/feedback/loop-action")
def submit_loop_action(payload: LoopActionRequest, request: Request) -> dict:
    action = payload.action.strip().lower()
    if action not in {"consult", "add_teaching_case", "add_rule", "add_retrain_sample"}:
        raise HTTPException(status_code=400, detail="invalid_action")

    record_event(
        event_type="feedback.loop_action",
        actor=resolve_actor(request, default="doctor"),
        details={
            "case_id": payload.case_id,
            "action": action,
            "comment": payload.comment,
        },
    )
    return {"status": "recorded", "action": action, "case_id": payload.case_id}
