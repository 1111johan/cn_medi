from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Query

from app.core.config import SYNDROME_RULES
from app.core.audit import query_events
from app.models.schemas import AuditRecord

router = APIRouter(tags=["governance"])


@router.get("/governance/audit", response_model=List[AuditRecord])
def governance_audit(
    actor: Optional[str] = Query(default=None),
    event_type: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
) -> List[AuditRecord]:
    records = query_events(actor=actor, event_type=event_type, limit=limit)
    return [AuditRecord(**item) for item in records]


@router.get("/governance/rules")
def governance_rules() -> dict:
    return {
        "count": len(SYNDROME_RULES),
        "rules": SYNDROME_RULES,
    }
