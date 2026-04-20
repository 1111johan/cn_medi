from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from .config import AUDIT_FILE
from .storage import JsonlStore


_audit_store = JsonlStore(AUDIT_FILE)


def record_event(event_type: str, actor: str, details: Dict[str, Any]) -> Dict[str, Any]:
    item = {
        "event_id": str(uuid4()),
        "timestamp": datetime.utcnow().isoformat(),
        "actor": actor,
        "event_type": event_type,
        "details": details,
    }
    _audit_store.append(item)
    return item


def query_events(
    actor: Optional[str] = None,
    event_type: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    records = _audit_store.read()
    if actor:
        records = [r for r in records if r.get("actor") == actor]
    if event_type:
        records = [r for r in records if r.get("event_type") == event_type]
    records.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return records[:limit]
