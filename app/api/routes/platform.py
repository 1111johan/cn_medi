from __future__ import annotations

from fastapi import APIRouter, Query

from app.models.schemas import PlatformOverview
from app.services.overview_service import overview_service
from app.services.platform_search_service import platform_search_service

router = APIRouter(tags=["platform"])


@router.get("/platform/overview", response_model=PlatformOverview)
def platform_overview() -> PlatformOverview:
    return PlatformOverview(**overview_service.metrics())


@router.get("/platform/dashboard")
def platform_dashboard() -> dict:
    return overview_service.dashboard()


@router.get("/platform/global-search")
def platform_global_search(
    q: str = Query(..., min_length=1),
    top_k: int = Query(default=20, ge=1, le=50),
) -> dict:
    return platform_search_service.search(query=q, top_k=top_k)
