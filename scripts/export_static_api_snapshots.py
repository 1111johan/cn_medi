from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.core.audit import query_events  # noqa: E402
from app.core.config import SYNDROME_RULES  # noqa: E402
from app.services.knowledge_service import knowledge_service  # noqa: E402
from app.services.overview_service import overview_service  # noqa: E402
from app.services.platform_search_service import platform_search_service  # noqa: E402
from app.services.professional_knowledge_service import professional_knowledge_service  # noqa: E402
from app.services.review_service import review_service  # noqa: E402
from app.services.smart_qa_service import smart_qa_service  # noqa: E402


EXPORT_DIR = ROOT_DIR / "frontend" / "public" / "api-static"


def write_json(relative_path: str, payload: Any) -> None:
    target = EXPORT_DIR / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def build_professional_search_index(limit: int = 400) -> List[Dict[str, Any]]:
    try:
        professional_knowledge_service._ensure_index_ready()  # type: ignore[attr-defined]
        with professional_knowledge_service._connect() as conn:  # type: ignore[attr-defined]
            rows = conn.execute(
                "SELECT object_id, title, content, source_type, source_path "
                "FROM professional_documents ORDER BY rowid DESC LIMIT ?",
                (limit,),
            ).fetchall()
    except (AttributeError, sqlite3.Error, OSError):
        return []

    items: List[Dict[str, Any]] = []
    for row in rows:
        content = str(row["content"] or "")
        items.append(
            {
                "object_id": str(row["object_id"]),
                "title": str(row["title"] or ""),
                "source_type": str(row["source_type"] or "professional"),
                "source_path": str(row["source_path"] or ""),
                "content": content[:600],
                "snippet": content[:220],
            }
        )
    return items


def build_search_corpus(
    knowledge_items: List[Dict[str, Any]],
    professional_items: List[Dict[str, Any]],
    review_payload: Dict[str, Any],
    audit_items: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    corpus: List[Dict[str, Any]] = []

    for item in knowledge_items:
        corpus.append(
            {
                "id": f"knowledge:{item.get('object_id', '')}",
                "category": "knowledge",
                "title": item.get("title", ""),
                "snippet": str(item.get("content", ""))[:180],
                "source": item.get("source_type", "knowledge"),
                "route": "/middle/knowledge",
            }
        )

    for item in professional_items:
        corpus.append(
            {
                "id": f"professional:{item.get('object_id', '')}",
                "category": "professional",
                "title": item.get("title", ""),
                "snippet": item.get("snippet", ""),
                "source": item.get("source_path", "professional"),
                "route": "/middle/knowledge",
            }
        )

    for syndrome, rule in SYNDROME_RULES.items():
        corpus.append(
            {
                "id": f"rule:{syndrome}",
                "category": "rule",
                "title": syndrome,
                "snippet": f"治法：{rule.get('therapy', '')}；方剂：{rule.get('formula', '')}",
                "source": "SYNDROME_RULES",
                "route": "/middle/reasoning",
            }
        )

    for item in smart_qa_service.list_scenarios():
        corpus.append(
            {
                "id": f"smart_qa:{item.get('name', '')}",
                "category": "smart_qa",
                "title": f"智慧问答场景：{item.get('name', '')}",
                "snippet": "；".join(item.get("keywords", [])[:6]),
                "source": "smart_qa_scenarios",
                "route": "/smart-qa",
            }
        )

    for task in review_payload.get("tasks", []):
        corpus.append(
            {
                "id": f"review:{task.get('task_id', '')}",
                "category": "review",
                "title": task.get("title", ""),
                "snippet": task.get("summary", ""),
                "source": task.get("status", "pending"),
                "route": "/review/expert",
            }
        )

    for event in audit_items[:80]:
        details = json.dumps(event.get("details", {}), ensure_ascii=False)
        corpus.append(
            {
                "id": f"audit:{event.get('event_id', '')}",
                "category": "audit",
                "title": event.get("event_type", "audit"),
                "snippet": details[:180],
                "source": event.get("actor", "system"),
                "route": "/governance/operations",
            }
        )

    return corpus


def main() -> None:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    knowledge_items = knowledge_service.all()[:500]
    dashboard = overview_service.dashboard()
    professional_stats = professional_knowledge_service.stats()
    professional_index = build_professional_search_index()
    review_payload = {
        "tasks": review_service.list_tasks(limit=240),
        "stats": review_service.stats(),
    }
    audit_items = query_events(limit=400)
    rules_payload = {
        "count": len(SYNDROME_RULES),
        "rules": SYNDROME_RULES,
    }
    scenario_payload = {
        "scenarios": smart_qa_service.list_scenarios(),
    }
    search_corpus = build_search_corpus(
        knowledge_items=knowledge_items,
        professional_items=professional_index,
        review_payload=review_payload,
        audit_items=audit_items,
    )

    write_json("health.json", {"status": "ok", "mode": "static_snapshot"})
    write_json("platform/dashboard.json", dashboard)
    write_json("platform/global-search.json", {"results": search_corpus, "total": len(search_corpus)})
    write_json("knowledge/list.json", knowledge_items)
    write_json("knowledge/search.json", {"items": knowledge_items})
    write_json("knowledge/professional/stats.json", professional_stats)
    write_json("knowledge/professional/search.json", {"results": professional_index})
    write_json("governance/audit.json", audit_items)
    write_json("governance/rules.json", rules_payload)
    write_json("review/tasks.json", review_payload)
    write_json("smart-qa/scenarios.json", scenario_payload)

    # Force import resolution so build fails early if upstream payload code breaks.
    _ = platform_search_service
    print(f"exported static api snapshots to {EXPORT_DIR}")


if __name__ == "__main__":
    main()
