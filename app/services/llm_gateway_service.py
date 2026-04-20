from __future__ import annotations

import json
from typing import Any, Dict, List
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.config import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_CHAT_MODEL,
    LLM_TIMEOUT_SECONDS,
    PRIMARY_LLM_MODEL,
    PRIMARY_LLM_PROVIDER,
    SELF_MODEL_NAME,
)


class LLMGatewayService:
    """LLM gateway for model providers used by the platform."""

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 700,
    ) -> Dict[str, Any]:
        provider = (PRIMARY_LLM_PROVIDER or "").strip().lower()
        if provider == "deepseek":
            return self._chat_deepseek(messages=messages, temperature=temperature, max_tokens=max_tokens)

        return {
            "ok": False,
            "provider": "self",
            "model": SELF_MODEL_NAME,
            "content": "",
            "error": f"unsupported_provider:{provider or 'unknown'}",
        }

    def _chat_deepseek(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> Dict[str, Any]:
        if not DEEPSEEK_API_KEY:
            return {
                "ok": False,
                "provider": "self",
                "model": SELF_MODEL_NAME,
                "content": "",
                "error": "service_key_missing",
            }

        model = (PRIMARY_LLM_MODEL or "").strip()
        if not model or "/" in model:
            model = DEEPSEEK_CHAT_MODEL

        url = f"{DEEPSEEK_BASE_URL.rstrip('/')}/chat/completions"
        payload = {
            "model": model,
            "messages": messages,
            "temperature": max(0.0, min(1.2, float(temperature))),
            "max_tokens": max(128, min(4096, int(max_tokens))),
        }
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = Request(
            url=url,
            method="POST",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            },
        )

        try:
            with urlopen(request, timeout=LLM_TIMEOUT_SECONDS) as response:
                body = response.read().decode("utf-8")
            parsed = json.loads(body)
            content = (
                parsed.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )

            if not content:
                return {
                    "ok": False,
                    "provider": "self",
                    "model": SELF_MODEL_NAME,
                    "content": "",
                    "error": "empty_content",
                    "raw": parsed,
                }

            return {
                "ok": True,
                "provider": "self",
                "model": SELF_MODEL_NAME,
                "content": str(content).strip(),
                "raw": parsed,
            }
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            return {
                "ok": False,
                "provider": "self",
                "model": SELF_MODEL_NAME,
                "content": "",
                "error": f"service_http_{exc.code}",
                "detail": detail[:600],
            }
        except URLError as exc:
            return {
                "ok": False,
                "provider": "self",
                "model": SELF_MODEL_NAME,
                "content": "",
                "error": "service_network_error",
                "detail": str(exc),
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "ok": False,
                "provider": "self",
                "model": SELF_MODEL_NAME,
                "content": "",
                "error": "service_unexpected_error",
                "detail": str(exc),
            }


llm_gateway_service = LLMGatewayService()
