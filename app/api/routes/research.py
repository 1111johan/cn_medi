from __future__ import annotations

from fastapi import APIRouter, Request

from app.api.routes.utils import resolve_actor
from app.core.audit import record_event
from app.models.schemas import ResearchQARequest, ResearchQAResponse
from app.services.research_service import research_service

router = APIRouter(tags=["research"])


@router.post("/research/qa", response_model=ResearchQAResponse)
def research_qa(payload: ResearchQARequest, request: Request) -> ResearchQAResponse:
    result = research_service.qa(
        question=payload.question,
        scope=payload.scope,
        source_types=payload.source_types,
    )
    record_event(
        event_type="research.qa",
        actor=resolve_actor(request),
        details={"question": payload.question, "evidence_count": len(result["evidences"])},
    )
    return ResearchQAResponse(**result)
