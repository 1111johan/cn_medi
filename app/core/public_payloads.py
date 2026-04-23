from __future__ import annotations

from typing import Any, Dict, Iterable, List


PUBLIC_AUDIT_DETAIL_KEYS = {
    "action",
    "alerts",
    "attachment_count",
    "available",
    "base_formula",
    "candidate_count",
    "draft_length",
    "evidence_count",
    "has_draft",
    "has_top_candidate",
    "image_type",
    "indexed_files",
    "missing_fields",
    "mode",
    "question_length",
    "record_count",
    "red_flags",
    "risk_level",
    "scenario",
    "source_type",
    "status",
    "syndrome",
    "task_status",
    "template_type",
    "top_syndrome",
}

PUBLIC_PROFESSIONAL_STATS_KEYS = (
    "available",
    "record_count",
    "indexed_files",
    "indexed_at",
)


def _sanitize_json_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list):
        return [_sanitize_json_value(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _sanitize_json_value(item) for key, item in value.items()}
    return str(value)


def sanitize_audit_details(details: Dict[str, Any] | None) -> Dict[str, Any]:
    payload = details if isinstance(details, dict) else {}
    return {
        key: _sanitize_json_value(payload[key])
        for key in PUBLIC_AUDIT_DETAIL_KEYS
        if key in payload
    }


def public_audit_record(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "event_id": str(item.get("event_id", "")),
        "timestamp": str(item.get("timestamp", "")),
        "actor": str(item.get("actor", "")),
        "event_type": str(item.get("event_type", "")),
        "details": sanitize_audit_details(item.get("details")),
    }


def public_audit_records(items: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [public_audit_record(item) for item in items]


def public_professional_stats(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        key: _sanitize_json_value(payload.get(key))
        for key in PUBLIC_PROFESSIONAL_STATS_KEYS
    }
