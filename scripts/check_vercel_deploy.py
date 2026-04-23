from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from typing import Any, Dict, List, Tuple


DEFAULT_TIMEOUT_SECONDS = 20


def _request(url: str) -> Tuple[int | None, str]:
    req = urllib.request.Request(url=url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT_SECONDS) as resp:
            body = resp.read().decode("utf-8", errors="ignore")
            return resp.status, body
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        return exc.code, body
    except urllib.error.URLError as exc:
        return None, f"URL error: {exc}"


def _preview(body: str, limit: int = 160) -> str:
    return " ".join(body.split())[:limit]


def _print_check(name: str, url: str, status: int | None, body: str) -> None:
    state = "OK" if status and 200 <= status < 300 else "FAIL"
    print(f"[{state}] {name}")
    print(f"  url: {url}")
    print(f"  status: {status if status is not None else 'unreachable'}")
    print(f"  body: {_preview(body)}")


def _manual_hints(results: Dict[str, Tuple[int | None, str]]) -> List[str]:
    hints: List[str] = []

    api_health_status = results["api_health"][0]
    static_list_status = results["static_knowledge_list"][0]

    if api_health_status in {404, None, 500, 502, 503, 504}:
        hints.append("检查 Vercel Project Settings -> General -> Root Directory，必须是仓库根目录，不要设成 frontend/")
        hints.append("检查 Vercel Project Settings -> Build & Development Settings，Build Command 不要覆盖成 cd frontend && npm run build")
        hints.append("检查 Deployments -> 当前部署 -> Functions / Logs，确认 /api/health 是否真的生成了 Python Function")

    if static_list_status == 404:
        hints.append("检查构建日志里是否出现 python3 scripts/export_static_api_snapshots.py")
        hints.append("确认 vercel.json 的 buildCommand 是 npm run build:frontend，而不是只跑 frontend 的 vite build")

    if api_health_status and 200 <= api_health_status < 300:
        hints.append("若 /api/health 正常但业务接口失败，继续检查 /api/knowledge/professional/stats 和对应函数日志")

    return hints


def main() -> int:
    parser = argparse.ArgumentParser(description="Check a Vercel deployment for API/static snapshot availability.")
    parser.add_argument("base_url", help="Deployment base URL, e.g. https://cn-medi-l7al.vercel.app")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    checks = [
        ("site_root", f"{base_url}/"),
        ("api_health", f"{base_url}/api/health"),
        ("api_professional_stats", f"{base_url}/api/knowledge/professional/stats"),
        ("static_knowledge_list", f"{base_url}/api-static/knowledge/list.json"),
        ("static_professional_stats", f"{base_url}/api-static/knowledge/professional/stats.json"),
    ]

    results: Dict[str, Tuple[int | None, str]] = {}
    for name, url in checks:
        status, body = _request(url)
        results[name] = (status, body)
        _print_check(name, url, status, body)

    print("\nSummary")
    print(json.dumps({name: status for name, (status, _) in results.items()}, ensure_ascii=False, indent=2))

    hints = _manual_hints(results)
    if hints:
        print("\nLikely Causes / Next Checks")
        for hint in hints:
            print(f"- {hint}")

    failures = [name for name, (status, _) in results.items() if not status or status >= 400]
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
