from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List
from uuid import uuid4

from app.core.config import DEFAULT_KNOWLEDGE, KNOWLEDGE_FILE
from app.core.storage import JsonListStore

STOPWORDS = {"的", "和", "与", "及", "如何", "什么", "怎么", "请问", "关于", "一下"}
DOMAIN_TERMS = [
    "脾虚",
    "痰湿",
    "瘀",
    "证候",
    "病机",
    "方剂",
    "归脾汤",
    "二陈汤",
    "血府逐瘀汤",
    "气血两虚",
    "痰湿瘀阻",
    "脾虚痰瘀",
]


class KnowledgeService:
    def __init__(self) -> None:
        self.store = JsonListStore(KNOWLEDGE_FILE)
        self.ensure_seed_data()

    def ensure_seed_data(self) -> None:
        data = self.store.read()
        if data:
            return

        seeded: List[Dict[str, Any]] = []
        now = datetime.utcnow().isoformat()
        for item in DEFAULT_KNOWLEDGE:
            seeded.append(
                {
                    "object_id": str(uuid4()),
                    "source_type": item["source_type"],
                    "title": item["title"],
                    "content": item["content"],
                    "tags": item.get("tags", []),
                    "metadata": item.get("metadata", {}),
                    "created_at": now,
                }
            )
        self.store.write(seeded)

    def ingest(self, payload: Dict[str, Any]) -> str:
        obj_id = str(uuid4())
        item = {
            "object_id": obj_id,
            "source_type": payload["source_type"],
            "title": payload["title"],
            "content": payload["content"],
            "tags": payload.get("tags", []),
            "metadata": payload.get("metadata", {}),
            "created_at": datetime.utcnow().isoformat(),
        }
        self.store.append(item)
        return obj_id

    def all(self) -> List[Dict[str, Any]]:
        return self.store.read()

    def count(self) -> int:
        return len(self.all())

    def search(self, query: str, source_types: List[str] | None = None, top_k: int = 5) -> List[Dict[str, Any]]:
        source_types = source_types or []
        terms = self._extract_terms(query)
        results: List[Dict[str, Any]] = []

        for item in self.all():
            if source_types and item.get("source_type") not in source_types:
                continue

            score = self._score(item, query, terms)
            if score <= 0:
                continue

            results.append(
                {
                    **item,
                    "score": round(score, 3),
                    "snippet": self._build_snippet(item.get("content", ""), terms),
                }
            )

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def _extract_terms(self, text: str) -> List[str]:
        text = text.strip()
        cleaned = re.sub(r"[^\w\u4e00-\u9fff]+", " ", text)
        terms = [t for t in cleaned.split() if len(t) >= 2 and t not in STOPWORDS]
        for domain_term in DOMAIN_TERMS:
            if domain_term in text:
                terms.append(domain_term)

        # 去重并保序
        dedup: List[str] = []
        seen = set()
        for term in terms:
            if term not in seen:
                seen.add(term)
                dedup.append(term)
        return dedup

    def _score(self, item: Dict[str, Any], query: str, terms: List[str]) -> float:
        score = 0.0
        title = item.get("title", "")
        content = item.get("content", "")
        tags = item.get("tags", [])

        if query and query in title:
            score += 3.0
        if query and query in content:
            score += 2.0

        for term in terms:
            if term in title:
                score += 1.5
            if term in content:
                score += 1.0
            if any(term in tag for tag in tags):
                score += 1.2

        return score

    def _build_snippet(self, content: str, terms: List[str], window: int = 80) -> str:
        if not content:
            return ""

        hit_pos = -1
        for term in terms:
            idx = content.find(term)
            if idx >= 0:
                hit_pos = idx
                break

        if hit_pos < 0:
            return content[:window]

        start = max(0, hit_pos - window // 2)
        end = min(len(content), start + window)
        return content[start:end]


knowledge_service = KnowledgeService()
