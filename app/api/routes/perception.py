from __future__ import annotations

from fastapi import APIRouter, Request

from app.api.routes.utils import resolve_actor
from app.core.audit import record_event
from app.models.schemas import PerceptionAnalyzeRequest, PerceptionAnalyzeResponse
from app.services.perception_service import perception_service

router = APIRouter(tags=["perception"])


@router.post("/perception/analyze", response_model=PerceptionAnalyzeResponse)
def analyze_perception(payload: PerceptionAnalyzeRequest, request: Request) -> PerceptionAnalyzeResponse:
    result = perception_service.analyze(
        image_type=payload.image_type,
        observations=payload.observations,
        notes=payload.notes,
    )
    record_event(
        event_type="perception.analyze",
        actor=resolve_actor(request),
        details={"image_type": payload.image_type, "alerts": result["alerts"]},
    )
    return PerceptionAnalyzeResponse(**result)
