from __future__ import annotations

import json
import socket
import ssl
import time
from typing import Any, Dict, List
from urllib.error import HTTPError, URLError
from urllib.request import HTTPSHandler, ProxyHandler, Request, build_opener

from app.core.config import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_BASE_URL_FALLBACK,
    DEEPSEEK_CHAT_MODEL,
    DEEPSEEK_DISABLE_SSL_VERIFY,
    DEEPSEEK_PROXY_URL,
    DEEPSEEK_RETRY_TIMES,
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
        # Keep DeepSeek as primary path even when deployment env accidentally keeps old provider values.
        if provider not in {"", "deepseek"} and DEEPSEEK_API_KEY:
            provider = "deepseek"

        if provider in {"", "deepseek"}:
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

        payload = {
            "model": model,
            "messages": messages,
            "temperature": max(0.0, min(1.2, float(temperature))),
            "max_tokens": max(128, min(4096, int(max_tokens))),
        }
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        ssl_context = self._build_ssl_context()
        opener = self._build_opener(ssl_context=ssl_context)
        retry_times = max(1, min(5, int(DEEPSEEK_RETRY_TIMES or 1)))
        errors: List[str] = []

        for endpoint in self._resolve_endpoints():
            for attempt in range(1, retry_times + 1):
                request = Request(
                    url=endpoint,
                    method="POST",
                    data=data,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                    },
                )
                try:
                    with opener.open(request, timeout=LLM_TIMEOUT_SECONDS) as response:
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
                    errors.append(f"{endpoint}#{attempt}:http_{exc.code}")
                    # Key/model errors should fail fast.
                    if exc.code in {400, 401, 403, 422}:
                        return {
                            "ok": False,
                            "provider": "self",
                            "model": SELF_MODEL_NAME,
                            "content": "",
                            "error": f"service_http_{exc.code}",
                            "detail": detail[:600],
                        }
                except (URLError, ssl.SSLError, socket.timeout, TimeoutError) as exc:
                    errors.append(f"{endpoint}#{attempt}:{type(exc).__name__}:{str(exc)[:220]}")
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"{endpoint}#{attempt}:unexpected:{str(exc)[:220]}")

                if attempt < retry_times:
                    time.sleep(0.35 * attempt)

        tips = (
            "网络不可达；若在外网VPN环境，请设置 DEEPSEEK_PROXY_URL，"
            "并确保 NO_PROXY 包含 127.0.0.1,localhost；"
            "若 VPN 注入证书可尝试 DEEPSEEK_DISABLE_SSL_VERIFY=1。"
        )
        return {
            "ok": False,
            "provider": "self",
            "model": SELF_MODEL_NAME,
            "content": "",
            "error": "service_network_error",
            "detail": f"{tips} attempts={'; '.join(errors[:6])}",
        }

    def _resolve_endpoints(self) -> List[str]:
        urls: List[str] = []
        for raw in [DEEPSEEK_BASE_URL, DEEPSEEK_BASE_URL_FALLBACK]:
            base = str(raw or "").strip().rstrip("/")
            if not base:
                continue
            endpoint = base if base.endswith("/chat/completions") else f"{base}/chat/completions"
            if endpoint not in urls:
                urls.append(endpoint)
        if not urls:
            urls.append("https://api.deepseek.com/chat/completions")
        return urls

    def _build_ssl_context(self) -> ssl.SSLContext:
        if DEEPSEEK_DISABLE_SSL_VERIFY:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            return context
        return ssl.create_default_context()

    def _build_opener(self, ssl_context: ssl.SSLContext):
        handlers = [HTTPSHandler(context=ssl_context)]
        proxy = str(DEEPSEEK_PROXY_URL or "").strip()
        if proxy:
            handlers.insert(
                0,
                ProxyHandler(
                    {
                        "http": proxy,
                        "https": proxy,
                    }
                ),
            )
        return build_opener(*handlers)


llm_gateway_service = LLMGatewayService()
