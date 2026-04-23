from __future__ import annotations

from fastapi import APIRouter, Request

from app.api.routes.utils import resolve_actor
from app.core.audit import record_event
from app.models.schemas import (
    ClinicalDemoAnalyzeRequest,
    ClinicalDemoAnalyzeResponse,
    ClinicalDemoCommitRequest,
    ClinicalDemoCommitResponse,
)
from app.services.clinical_service import clinical_service

router = APIRouter(tags=["clinical_demo"])


@router.get("/clinical/demo-cases")
def clinical_demo_cases() -> dict:
    return {"cases": clinical_service.list_demo_patients()}


@router.post("/clinical/demo-analyze", response_model=ClinicalDemoAnalyzeResponse)
def clinical_demo_analyze(payload: ClinicalDemoAnalyzeRequest, request: Request) -> ClinicalDemoAnalyzeResponse:
    result = clinical_service.analyze(payload.model_dump())
    record_event(
        event_type="clinical.demo_analyze",
        actor=resolve_actor(request, default="doctor"),
        details={
            "case_id": result.get("case_id"),
            "patient_id": result.get("patient_id"),
            "top_syndrome": (result.get("top_syndromes") or [{}])[0].get("name", ""),
        },
    )
    return ClinicalDemoAnalyzeResponse(**result)


@router.post("/clinical/demo-commit", response_model=ClinicalDemoCommitResponse)
def clinical_demo_commit(payload: ClinicalDemoCommitRequest, request: Request) -> ClinicalDemoCommitResponse:
    result = clinical_service.commit(payload.model_dump(), actor=resolve_actor(request, default="doctor"))
    return ClinicalDemoCommitResponse(**result)
