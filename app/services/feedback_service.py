from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List
from uuid import uuid4

from app.core.config import FEEDBACK_FILE
from app.core.storage import JsonListStore


class FeedbackService:
    def __init__(self) -> None:
        self.store = JsonListStore(FEEDBACK_FILE)

    def submit(self, payload: Dict[str, Any]) -> str:
        feedback_id = str(uuid4())
        item = {
            "feedback_id": feedback_id,
            "created_at": datetime.utcnow().isoformat(),
            **payload,
        }
        self.store.append(item)
        return feedback_id

    def all(self) -> List[Dict[str, Any]]:
        return self.store.read()

    def count(self) -> int:
        return len(self.all())


feedback_service = FeedbackService()
