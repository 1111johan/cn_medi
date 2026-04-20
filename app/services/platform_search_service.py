from __future__ import annotations

import json
from typing import Any, Dict, List

from app.core.audit import query_events
from app.core.config import SYNDROME_RULES
from app.services.knowledge_service import knowledge_service
from app.services.professional_knowledge_service import professional_knowledge_service
from app.services.review_service import review_service
from app.services.smart_qa_service import smart_qa_service


class PlatformSearchService:
    def search(self, query: str, top_k: int = 20) -> Dict[str, Any]:
        q = query.strip()
        if not q:
            return {"query": query, "total": 0, "results": []}

        results: List[Dict[str, Any]] = []
        results.extend(self._search_knowledge(q))
        results.extend(self._search_professional(q))
        results.extend(self._search_rules(q))
        results.extend(self._search_smart_qa(q))
        results.extend(self._search_review_tasks(q))
        results.extend(self._search_audits(q))

        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        dedup: List[Dict[str, Any]] = []
        seen = set()
        for item in results:
            item_id = item.get("id")
            if item_id in seen:
                continue
            seen.add(item_id)
            dedup.append(item)
            if len(dedup) >= top_k:
                break

        return {
            "query": query,
            "total": len(dedup),
            "results": dedup,
        }

    def _search_knowledge(self, query: str) -> List[Dict[str, Any]]:
        items = knowledge_service.search(query=query, top_k=8)
        return [
            {
                "id": f"knowledge:{item['object_id']}",
                "category": "knowledge",
                "title": item["title"],
                "snippet": item.get("snippet", ""),
                "source": item.get("source_type", "knowledge"),
                "route": "/middle/knowledge",
                "score": float(item.get("score", 0)) + 2.4,
            }
            for item in items
        ]

    def _search_professional(self, query: str) -> List[Dict[str, Any]]:
        items = professional_knowledge_service.search(query=query, top_k=8)
        return [
            {
                "id": f"professional:{item['object_id']}",
                "category": "professional",
                "title": item["title"],
                "snippet": item.get("snippet", ""),
                "source": item.get("source_path", "professional"),
                "route": "/middle/knowledge",
                "score": float(item.get("score", 0)) + 1.5,
            }
            for item in items
        ]

    def _search_rules(self, query: str) -> List[Dict[str, Any]]:
        hits: List[Dict[str, Any]] = []
        for syndrome, rule in SYNDROME_RULES.items():
            corpus = " ".join([
                syndrome,
                rule.get("therapy", ""),
                rule.get("formula", ""),
                " ".join(rule.get("symptoms", [])),
            ])
            if query not in corpus and not any(term in corpus for term in query.split()):
                continue
            snippet = f"治法：{rule.get('therapy', '')}；方药：{rule.get('formula', '')}"
            hits.append(
                {
                    "id": f"rule:{syndrome}",
                    "category": "rule",
                    "title": syndrome,
                    "snippet": snippet,
                    "source": "SYNDROME_RULES",
                    "route": "/middle/reasoning",
                    "score": 8.5,
                }
            )
        return hits

    def _search_review_tasks(self, query: str) -> List[Dict[str, Any]]:
        tasks = review_service.list_tasks(limit=120)
        hits: List[Dict[str, Any]] = []
        for task in tasks:
            hay = " ".join(
                [
                    task.get("title", ""),
                    task.get("summary", ""),
                    task.get("ai_prejudge", ""),
                    " ".join(task.get("evidence_refs", [])),
                ]
            )
            if query not in hay and not any(part in hay for part in query.split()):
                continue
            hits.append(
                {
                    "id": f"review:{task.get('task_id')}",
                    "category": "review",
                    "title": task.get("title", ""),
                    "snippet": task.get("summary", ""),
                    "source": task.get("status", "pending"),
                    "route": "/review/expert",
                    "score": 7.2 if task.get("priority") == "high" else 6.4,
                }
            )
        return hits

    def _search_smart_qa(self, query: str) -> List[Dict[str, Any]]:
        items = smart_qa_service.list_scenarios()
        hits: List[Dict[str, Any]] = []
        for item in items:
            name = item.get("name", "")
            keywords = " ".join(item.get("keywords", []))
            steps = " ".join(item.get("steps", []))
            hay = f"智慧问答 数字人 咨询 {name} {keywords} {steps}"
            if query not in hay and not any(term in hay for term in query.split()):
                continue
            hits.append(
                {
                    "id": f"smart_qa:{name}",
                    "category": "smart_qa",
                    "title": f"智慧问答场景：{name}",
                    "snippet": f"关键词：{keywords}",
                    "source": "smart_qa_scenarios",
                    "route": "/smart-qa",
                    "score": 7.6,
                }
            )
        return hits

    def _search_audits(self, query: str) -> List[Dict[str, Any]]:
        events = query_events(limit=200)
        hits: List[Dict[str, Any]] = []
        for event in events:
            details = event.get("details", {})
            detail_text = json.dumps(details, ensure_ascii=False)
            hay = " ".join([event.get("event_type", ""), event.get("actor", ""), detail_text])
            if query not in hay and not any(part in hay for part in query.split()):
                continue
            hits.append(
                {
                    "id": f"audit:{event.get('event_id')}",
                    "category": "audit",
                    "title": event.get("event_type", "audit"),
                    "snippet": detail_text[:160],
                    "source": event.get("actor", "system"),
                    "route": "/governance/operations",
                    "score": 5.8,
                }
            )
            if len(hits) >= 8:
                break
        return hits


platform_search_service = PlatformSearchService()
