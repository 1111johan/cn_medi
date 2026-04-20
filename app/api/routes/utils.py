from __future__ import annotations

from fastapi import Request


def resolve_actor(request: Request, default: str = "system") -> str:
    actor = request.headers.get("x-actor")
    if actor:
        return actor
    return default
