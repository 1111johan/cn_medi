from __future__ import annotations

from typing import List

from fastapi import APIRouter, Query, Request

from app.api.routes.utils import resolve_actor
from app.core.audit import record_event
from app.models.schemas import KnowledgeIngestRequest, KnowledgeIngestResponse, KnowledgeObject, KnowledgeSearchItem
from app.services.knowledge_service import knowledge_service
from app.services.professional_knowledge_service import professional_knowledge_service

router = APIRouter(tags=["knowledge"])


@router.post("/knowledge/ingest", response_model=KnowledgeIngestResponse)
def ingest_knowledge(payload: KnowledgeIngestRequest, request: Request) -> KnowledgeIngestResponse:
    object_id = knowledge_service.ingest(payload.model_dump())
    record_event(
        event_type="knowledge.ingest",
        actor=resolve_actor(request),
        details={"object_id": object_id, "source_type": payload.source_type, "title": payload.title},
    )
    return KnowledgeIngestResponse(object_id=object_id, index_status="indexed")


@router.get("/knowledge/search", response_model=List[KnowledgeSearchItem])
def search_knowledge(
    q: str = Query(..., min_length=1),
    source_types: List[str] = Query(default_factory=list),
    top_k: int = Query(default=5, ge=1, le=20),
) -> List[KnowledgeSearchItem]:
    results = knowledge_service.search(query=q, source_types=source_types, top_k=top_k)
    return [KnowledgeSearchItem(**r) for r in results]


@router.get("/knowledge/list", response_model=List[KnowledgeObject])
def list_knowledge(limit: int = Query(default=50, ge=1, le=500)) -> List[KnowledgeObject]:
    data = knowledge_service.all()[:limit]
    return [KnowledgeObject(**item) for item in data]


@router.get("/knowledge/professional/stats")
def professional_knowledge_stats() -> dict:
    return professional_knowledge_service.stats()


@router.get("/knowledge/professional/search")
def professional_knowledge_search(
    q: str = Query(..., min_length=1),
    top_k: int = Query(default=8, ge=1, le=30),
) -> dict:
    return {
        "query": q,
        "results": professional_knowledge_service.search(query=q, top_k=top_k),
    }
