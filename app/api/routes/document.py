from __future__ import annotations

from fastapi import APIRouter, Request

from app.api.routes.utils import resolve_actor
from app.core.audit import record_event
from app.models.schemas import DocumentDraftRequest, DocumentDraftResponse
from app.services.document_service import document_service

router = APIRouter(tags=["document"])


@router.post("/document/draft", response_model=DocumentDraftResponse)
def draft_document(payload: DocumentDraftRequest, request: Request) -> DocumentDraftResponse:
    draft = document_service.draft(
        template_type=payload.template_type,
        patient_info=payload.patient_info,
        visit_data=payload.visit_data,
        reasoning_result=payload.reasoning_result,
    )
    record_event(
        event_type="document.draft",
        actor=resolve_actor(request),
        details={"template_type": payload.template_type, "draft_length": len(draft)},
    )
    return DocumentDraftResponse(draft=draft)
