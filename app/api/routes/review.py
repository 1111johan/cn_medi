from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.api.routes.utils import resolve_actor
from app.core.audit import record_event
from app.services.review_service import review_service

router = APIRouter(tags=["review"])


class ReviewDecisionRequest(BaseModel):
    action: str = Field(..., description="approve | reject | modify | escalate")
    comment: Optional[str] = None


@router.get("/review/tasks")
def review_tasks(
    status: Optional[str] = Query(default=None),
    task_type: Optional[str] = Query(default=None),
    priority: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> dict:
    tasks = review_service.list_tasks(
        status=status,
        task_type=task_type,
        priority=priority,
        limit=limit,
    )
    return {
        "tasks": tasks,
        "stats": review_service.stats(),
    }


@router.get("/review/tasks/{task_id}")
def review_task_detail(task_id: str) -> dict:
    task = review_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task_not_found")
    return task


@router.post("/review/tasks/{task_id}/decision")
def review_task_decision(task_id: str, payload: ReviewDecisionRequest, request: Request) -> dict:
    action = payload.action.strip().lower()
    if action not in {"approve", "reject", "modify", "escalate"}:
        raise HTTPException(status_code=400, detail="invalid_action")

    reviewer = resolve_actor(request, default="expert")

    try:
        updated = review_service.decide(
            task_id=task_id,
            action=action,
            reviewer=reviewer,
            comment=payload.comment,
        )
    except ValueError:
        raise HTTPException(status_code=404, detail="task_not_found")

    record_event(
        event_type="review.decision",
        actor=reviewer,
        details={
            "task_id": task_id,
            "action": action,
            "status": updated.get("status"),
        },
    )
    return updated
