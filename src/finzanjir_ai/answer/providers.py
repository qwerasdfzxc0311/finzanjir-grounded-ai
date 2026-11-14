from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

import httpx


logger = logging.getLogger(__name__)


class LLMGateway:
    """Small provider gateway: Gemini primary, OpenRouter fallback.

    API keys are read only from server environment variables and are never returned
    in responses or logs. The gateway returns None when no provider is configured
    or every provider fails, allowing the deterministic grounded fallback to run.
    """

    def __init__(self, environ: dict[str, str] | None = None) -> None:
        self.environ = environ if environ is not None else os.environ
        self.last_status = "not_attempted"
        self.last_provider_failures: list[dict[str, str]] = []

    def configured_providers(self) -> tuple[str, ...]:
        preference = self.environ.get("FINZANJIR_LLM_PROVIDER", "auto").strip().casefold()
        has_gemini = bool(self.environ.get("GEMINI_API_KEY"))
        has_router = bool(self.environ.get("OPENROUTER_API_KEY"))
        if preference == "gemini":
            return ("gemini",) if has_gemini else ()
        if preference == "openrouter":
            return ("openrouter",) if has_router else ()
        providers = []
        if has_gemini:
            providers.append("gemini")
        if has_router:
            providers.append("openrouter")
        return tuple(providers)

    def _record_failure(
        self,
        provider: str,
        category: str,
        *,
        http_status: int | None = None,
    ) -> None:
        """Record a sanitized provider failure without logging prompts or exception details."""
        self.last_provider_failures.append({"provider": provider, "status": category})
        if http_status is None:
            logger.warning(
                "LLM provider attempt failed: provider=%s category=%s",
                provider,
                category,
            )
            return
        logger.warning(
            "LLM provider attempt failed: provider=%s category=%s http_status=%d",
            provider,
            category,
            http_status,
        )

    def generate_json(self, *, system: str, prompt: str, max_output_tokens: int = 1800) -> dict[str, Any] | None:
        providers = self.configured_providers()
        if not providers:
            self.last_status = "not_configured"
            return None

        self.last_status = "provider_failed"
        self.last_provider_failures = []
        for provider in providers:
            try:
                raw = self._generate_with(provider, system, prompt, max_output_tokens)
                parsed = self._parse_json(raw)
                if isinstance(parsed, dict):
                    self.last_status = "ready"
                    return parsed
                self._record_failure(provider, "invalid_response")
            except httpx.HTTPStatusError as exc:
                code = exc.response.status_code
                if code in (401, 403):
                    category = "authentication_or_permission_failed"
                elif code == 429:
                    category = "rate_limited"
                elif code >= 500:
                    category = "provider_unavailable"
                else:
                    category = "request_rejected"
                self._record_failure(provider, category, http_status=code)
            except httpx.TimeoutException:
                self._record_failure(provider, "timeout")
            except httpx.NetworkError:
                self._record_failure(provider, "network_error")
            except httpx.HTTPError:
                self._record_failure(provider, "network_error")
            except (ValueError, KeyError, IndexError, TypeError):
                # Never expose provider response bodies, exception text, or keys.
                self._record_failure(provider, "invalid_response")
        return None

    def _generate_with(self, provider: str, system: str, prompt: str, max_output_tokens: int) -> str:
        timeout = httpx.Timeout(28.0, connect=6.0)
        if provider == "gemini":
            model = self.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
            key = self.environ["GEMINI_API_KEY"]
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            payload = {
                "systemInstruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "temperature": 0.25,
                    "maxOutputTokens": max_output_tokens,
                },
            }
            response = httpx.post(url, headers={"x-goog-api-key": key}, json=payload, timeout=timeout)
            response.raise_for_status()
            body = response.json()
            return body["candidates"][0]["content"]["parts"][0]["text"]

        model = self.environ.get("OPENROUTER_MODEL", "google/gemini-3.8-flash")
        key = self.environ["OPENROUTER_API_KEY"]
        response = httpx.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.25,
                "max_tokens": max_output_tokens,
                "response_format": {"type": "json_object"},
            },
            timeout=timeout,
        )
        response.raise_for_status()
        body = response.json()
        return body["choices"][0]["message"]["content"]

    @staticmethod
    def _parse_json(raw: str) -> dict[str, Any] | None:
        text = str(raw).strip()
        text = re.sub(r"^\x60{3}(?:json)?\s*|\s*\x60{3}$", "", text, flags=re.IGNORECASE)
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end <= start:
            return None
        value = json.loads(text[start:end + 1])
        return value if isinstance(value, dict) else None

    @staticmethod
    def can_send_text(text: str) -> bool:
        # Keep common personal/payment identifiers out of third-party model calls.
        if re.search(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)", text):
            return False
        if re.search(r"(?<!\w)[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}(?!\w)", text):
            return False
        if re.search(r"(?<!\d)\+?998[\s()-]?(?:\d[\s()-]?){9}(?!\d)", text):
            return False
        return True

    def expand_question(self, question: str) -> tuple[str, ...]:
        if not self.can_send_text(question):
            self.last_status = "blocked_sensitive"
            return ()
        result = self.generate_json(
            system=(
                "You are a multilingual query-understanding component for a closed-domain "
                "knowledge assistant. Do not answer the question and do not add facts."
            ),
            prompt=(
                "Interpret the user's intent, including spelling mistakes, abbreviations, "
                "colloquial Uzbek, Russian/English/Kazakh/Karakalpak variants, synonyms and "
                "indirect phrasing. Produce 3-7 short search queries that preserve the same "
                "meaning and help find relevant passages in the supplied project's knowledge "
                "base. Include the original language and, when useful, a standard Uzbek "
                "form. Do not invent project concepts. Return JSON: "
                '{"search_queries":["..."]}.\nQuestion: ' + question
            ),
            max_output_tokens=500,
        )
        if not result:
            return ()
        queries = result.get("search_queries", [])
        if not isinstance(queries, list):
            return ()
        cleaned = []
        for value in queries[:7]:
            text = str(value).strip()
            if text and text.casefold() != question.strip().casefold():
                cleaned.append(text[:240])
        return tuple(dict.fromkeys(cleaned))
