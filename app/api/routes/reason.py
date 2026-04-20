from __future__ import annotations

from fastapi import APIRouter, Request

from app.api.routes.utils import resolve_actor
from app.core.audit import record_event
from app.models.schemas import (
    FormulaReasonRequest,
    FormulaReasonResponse,
    SyndromeReasonRequest,
    SyndromeReasonResponse,
)
from app.services.reasoning_service import reasoning_service

router = APIRouter(tags=["reason"])


@router.post("/reason/syndrome", response_model=SyndromeReasonResponse)
def reason_syndrome(payload: SyndromeReasonRequest, request: Request) -> SyndromeReasonResponse:
    candidates = reasoning_service.reason_syndrome(
        symptoms=payload.symptoms,
        tongue_tags=payload.tongue_tags,
        pulse_tags=payload.pulse_tags,
        constraints=payload.constraints,
    )
    top = candidates[0]["syndrome"] if candidates else ""
    record_event(
        event_type="reason.syndrome",
        actor=resolve_actor(request),
        details={"top_syndrome": top, "candidate_count": len(candidates)},
    )
    return SyndromeReasonResponse(candidates=candidates)


@router.post("/reason/formula", response_model=FormulaReasonResponse)
def reason_formula(payload: FormulaReasonRequest, request: Request) -> FormulaReasonResponse:
    result = reasoning_service.reason_formula(
        syndrome=payload.syndrome,
        contraindications=payload.contraindications,
        patient_profile=payload.patient_profile,
    )
    record_event(
        event_type="reason.formula",
        actor=resolve_actor(request),
        details={"syndrome": payload.syndrome, "base_formula": result["base_formula"]},
    )
    return FormulaReasonResponse(**result)


@router.post("/reason/trace")
def reason_trace(payload: SyndromeReasonRequest, request: Request) -> dict:
    result = reasoning_service.reason_trace(
        symptoms=payload.symptoms,
        tongue_tags=payload.tongue_tags,
        pulse_tags=payload.pulse_tags,
        constraints=payload.constraints,
    )
    record_event(
        event_type="reason.trace",
        actor=resolve_actor(request),
        details={"has_top_candidate": bool(result.get("top_candidate"))},
    )
    return result
