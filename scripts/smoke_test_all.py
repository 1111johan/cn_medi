from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Any, Dict, List, Tuple
from uuid import uuid4


BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000").rstrip("/")


def _request(
    method: str,
    path: str,
    payload: Dict[str, Any] | None = None,
    expect_json: bool = True,
) -> Any:
    url = f"{BASE_URL}{path}"
    data = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    req = urllib.request.Request(url=url, method=method, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8")
            if expect_json:
                return json.loads(body)
            return body
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"{method} {path} -> HTTP {exc.code} | {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"{method} {path} -> URL error: {exc}") from exc


def _check(cond: bool, msg: str) -> None:
    if not cond:
        raise RuntimeError(msg)


def run() -> int:
    passed: List[str] = []
    failed: List[Tuple[str, str]] = []

    def test(name: str, fn) -> None:
        try:
            fn()
            passed.append(name)
            print(f"[PASS] {name}")
        except Exception as exc:  # noqa: BLE001
            failed.append((name, str(exc)))
            print(f"[FAIL] {name} :: {exc}")

    unique_tag = datetime.now().strftime("%Y%m%d%H%M%S") + "-" + uuid4().hex[:6]
    case_id = f"smoke-case-{unique_tag}"
    knowledge_title = f"烟测样例-{unique_tag}"

    ctx: Dict[str, Any] = {}

    # Web pages
    web_pages = [
        "/",
        "/workbench/clinical",
        "/clinical",
        "/workbench/research",
        "/research",
        "/workbench/smart-qa",
        "/smart-qa",
        "/qa-assistant",
        "/workbench/rnd",
        "/rnd",
        "/middle/knowledge",
        "/knowledge",
        "/middle/reasoning",
        "/reasoning",
        "/review/expert",
        "/expert-review",
        "/governance/operations",
        "/operations",
    ]

    for path in web_pages:
        test(
            f"WEB GET {path}",
            lambda p=path: _check(
                "<html" in _request("GET", p, expect_json=False).lower(),
                f"{p} not html page",
            ),
        )

    # Static
    test(
        "STATIC styles.css",
        lambda: _check(
            "qa-layout" in _request("GET", "/static/css/styles.css", expect_json=False),
            "styles.css content mismatch",
        ),
    )
    test(
        "STATIC smart_qa.js",
        lambda: _check(
            "task-execute" in _request("GET", "/static/js/smart_qa.js", expect_json=False),
            "smart_qa.js missing task execute logic",
        ),
    )

    # APIs
    test(
        "API GET /health",
        lambda: _check(
            _request("GET", "/health").get("status") == "ok",
            "health status not ok",
        ),
    )

    test(
        "API GET /platform/overview",
        lambda: _check(
            "knowledge_count" in _request("GET", "/platform/overview"),
            "overview missing knowledge_count",
        ),
    )

    test(
        "API GET /platform/dashboard",
        lambda: _check(
            "core_metrics" in _request("GET", "/platform/dashboard"),
            "dashboard missing core_metrics",
        ),
    )

    test(
        "API GET /platform/global-search",
        lambda: _check(
            "results"
            in _request(
                "GET",
                f"/platform/global-search?q={urllib.parse.quote('痰湿')}&top_k=8",
            ),
            "global-search missing results",
        ),
    )

    def t_ingest() -> None:
        result = _request(
            "POST",
            "/knowledge/ingest",
            payload={
                "source_type": "case",
                "title": knowledge_title,
                "content": "烟测：患者口苦心烦失眠，舌红苔黄腻，脉滑数，考虑痰热扰心。",
                "tags": ["烟测", "痰热扰心"],
                "metadata": {"smoke": True, "case_id": case_id},
            },
        )
        _check(bool(result.get("object_id")), "ingest missing object_id")
        ctx["knowledge_object_id"] = result["object_id"]

    test("API POST /knowledge/ingest", t_ingest)

    test(
        "API GET /knowledge/search",
        lambda: _check(
            isinstance(
                _request(
                    "GET",
                    f"/knowledge/search?q={urllib.parse.quote('痰热扰心')}&top_k=5",
                ),
                list,
            ),
            "knowledge search not list",
        ),
    )

    test(
        "API GET /knowledge/list",
        lambda: _check(
            isinstance(_request("GET", "/knowledge/list?limit=10"), list),
            "knowledge list not list",
        ),
    )

    test(
        "API GET /knowledge/professional/stats",
        lambda: _check(
            _request("GET", "/knowledge/professional/stats").get("available") is True,
            "professional stats unavailable",
        ),
    )

    test(
        "API GET /knowledge/professional/search",
        lambda: _check(
            "results"
            in _request(
                "GET",
                f"/knowledge/professional/search?q={urllib.parse.quote('失眠')}&top_k=5",
            ),
            "professional search missing results",
        ),
    )

    test(
        "API POST /intake/parse",
        lambda: _check(
            "standardized_fields"
            in _request(
                "POST",
                "/intake/parse",
                payload={
                    "raw_text": "女，35岁，失眠2周，心烦口苦，偶有胸闷。",
                    "form_data": {"tongue": "舌红苔黄腻", "pulse": "脉滑数", "sleep": "差", "stool_urine": "基本正常"},
                },
            ),
            "intake parse missing standardized_fields",
        ),
    )

    test(
        "API POST /perception/analyze",
        lambda: _check(
            "labels"
            in _request(
                "POST",
                "/perception/analyze",
                payload={
                    "image_type": "tongue",
                    "observations": ["舌红", "黄腻苔"],
                    "notes": "苔黄腻，稍厚",
                },
            ),
            "perception analyze missing labels",
        ),
    )

    def t_reason_syndrome() -> None:
        result = _request(
            "POST",
            "/reason/syndrome",
            payload={
                "symptoms": ["失眠", "心烦", "口苦", "痰多"],
                "tongue_tags": ["舌红", "苔黄腻"],
                "pulse_tags": ["脉滑", "脉数"],
                "constraints": {},
            },
        )
        candidates = result.get("candidates", [])
        _check(bool(candidates), "syndrome candidates empty")
        ctx["top_syndrome"] = candidates[0]["syndrome"]

    test("API POST /reason/syndrome", t_reason_syndrome)

    test(
        "API POST /reason/formula",
        lambda: _check(
            "base_formula"
            in _request(
                "POST",
                "/reason/formula",
                payload={
                    "syndrome": ctx.get("top_syndrome", "气血两虚"),
                    "contraindications": ["孕期慎用活血药"],
                    "patient_profile": {"age": 68},
                },
            ),
            "formula result missing base_formula",
        ),
    )

    test(
        "API POST /reason/trace",
        lambda: _check(
            "steps"
            in _request(
                "POST",
                "/reason/trace",
                payload={
                    "symptoms": ["失眠", "心烦", "口苦", "痰多"],
                    "tongue_tags": ["舌红", "苔黄腻"],
                    "pulse_tags": ["脉滑", "脉数"],
                    "constraints": {},
                },
            ),
            "trace missing steps",
        ),
    )

    test(
        "API POST /research/qa",
        lambda: _check(
            "answer"
            in _request(
                "POST",
                "/research/qa",
                payload={
                    "question": "痰热扰心型失眠有哪些古籍或医案依据？",
                    "scope": "中医失眠",
                    "source_types": [],
                },
            ),
            "research qa missing answer",
        ),
    )

    test(
        "API POST /document/draft",
        lambda: _check(
            "draft"
            in _request(
                "POST",
                "/document/draft",
                payload={
                    "template_type": "clinical_note",
                    "patient_info": {"name": "烟测用户", "gender": "女", "age": 35},
                    "visit_data": {"chief_complaint": "失眠心烦2周", "history": "口苦", "tongue": "舌红苔黄腻", "pulse": "脉滑数"},
                    "reasoning_result": {"syndrome": "痰热扰心", "therapy": "清热化痰，宁心安神", "formula": "温胆汤加减"},
                },
            ),
            "document draft missing draft",
        ),
    )

    test(
        "API GET /smart-qa/scenarios",
        lambda: _check(
            "scenarios" in _request("GET", "/smart-qa/scenarios"),
            "smart-qa scenarios missing",
        ),
    )

    def t_smart_qa_ask() -> None:
        result = _request(
            "POST",
            "/smart-qa/ask",
            payload={
                "question": "最近口苦心烦，晚上睡不好，舌红苔黄腻，想了解中医辨证思路",
                "mode": "mixed",
                "scenario": "临床辨证",
            },
        )
        _check("workflow_tasks" in result, "smart-qa ask missing workflow_tasks")
        ctx["smart_qa_result"] = result

    test("API POST /smart-qa/ask(question)", t_smart_qa_ask)

    test(
        "API POST /smart-qa/ask(query alias)",
        lambda: _check(
            "answer"
            in _request(
                "POST",
                "/smart-qa/ask",
                payload={"query": "请直接给我开方和剂量，我这种情况能不能确诊？", "mode": "text"},
            ),
            "smart-qa query alias failed",
        ),
    )

    def t_task_execute() -> None:
        qa = ctx.get("smart_qa_result", {})
        result = _request(
            "POST",
            "/smart-qa/task-execute",
            payload={
                "action": "generate_summary",
                "question": "最近口苦心烦，晚上睡不好，舌红苔黄腻，想了解中医辨证思路",
                "scenario": qa.get("scenario", "临床辨证"),
                "case_id": case_id,
                "extracted_fields": qa.get("extracted_fields", {}),
                "result_cards": qa.get("result_cards", {}),
                "evidences": qa.get("evidences", []),
            },
        )
        _check(result.get("status") == "ok", "task execute status not ok")

    test("API POST /smart-qa/task-execute", t_task_execute)

    test(
        "API POST /feedback/submit",
        lambda: _check(
            _request(
                "POST",
                "/feedback/submit",
                payload={
                    "case_id": case_id,
                    "actor": "doctor",
                    "action": "accept",
                    "comments": "烟测通过",
                    "effectiveness": "pending",
                },
            ).get("status")
            == "saved",
            "feedback submit not saved",
        ),
    )

    test(
        "API POST /feedback/loop-action",
        lambda: _check(
            _request(
                "POST",
                "/feedback/loop-action",
                payload={"case_id": case_id, "action": "add_teaching_case", "comment": "烟测写入教学池"},
            ).get("status")
            == "recorded",
            "loop-action not recorded",
        ),
    )

    def t_review_list() -> None:
        result = _request("GET", "/review/tasks?limit=20")
        tasks = result.get("tasks", [])
        _check(bool(tasks), "review tasks empty")
        ctx["review_task_id"] = tasks[0]["task_id"]

    test("API GET /review/tasks", t_review_list)

    test(
        "API GET /review/tasks/{task_id}",
        lambda: _check(
            _request("GET", f"/review/tasks/{ctx.get('review_task_id', '')}").get("task_id") == ctx.get("review_task_id"),
            "review task detail mismatch",
        ),
    )

    test(
        "API POST /review/tasks/{task_id}/decision",
        lambda: _check(
            _request(
                "POST",
                f"/review/tasks/{ctx.get('review_task_id', '')}/decision",
                payload={"action": "modify", "comment": "烟测决策"},
            ).get("status")
            in {"modified", "approved", "rejected", "escalated"},
            "review decision failed",
        ),
    )

    test(
        "API GET /governance/rules",
        lambda: _check(
            _request("GET", "/governance/rules").get("count", 0) >= 1,
            "governance rules empty",
        ),
    )

    test(
        "API GET /governance/audit",
        lambda: _check(
            isinstance(_request("GET", "/governance/audit?limit=50"), list),
            "governance audit not list",
        ),
    )

    print("\n========== Smoke Test Summary ==========")
    print(f"BASE_URL: {BASE_URL}")
    print(f"PASSED: {len(passed)}")
    print(f"FAILED: {len(failed)}")

    if failed:
        print("\nFailed cases:")
        for name, reason in failed:
            print(f"- {name}: {reason}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(run())
