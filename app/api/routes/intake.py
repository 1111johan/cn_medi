from __future__ import annotations

from fastapi import APIRouter, Request

from app.api.routes.utils import resolve_actor
from app.core.audit import record_event
from app.models.schemas import IntakeParseRequest, IntakeParseResponse
from app.services.intake_service import intake_service

router = APIRouter(tags=["intake"])


@router.post("/intake/parse", response_model=IntakeParseResponse)
def parse_intake(payload: IntakeParseRequest, request: Request) -> IntakeParseResponse:
    result = intake_service.parse(raw_text=payload.raw_text, form_data=payload.form_data)
    record_event(
        event_type="intake.parse",
        actor=resolve_actor(request),
        details={"missing_fields": result["missing_fields"], "red_flags": result["red_flags"]},
    )
    return IntakeParseResponse(**result)
