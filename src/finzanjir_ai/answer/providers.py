from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

import httpx


logger = logging.getLogger(__name__)

# ISO 13616 IBAN country prefixes. A candidate must also pass the mod-97
# checksum; this avoids treating acronyms such as BM25 as bank identifiers.
_IBAN_COUNTRY_CODES = frozenset("""
AD AE AL AT AZ BA BE BG BH BI BJ BR BY CH CI CM CR CV CY CZ DE DJ DK DO DZ
EE EG ES FI FO FR GB GE GI GL GQ GR GT GW HN HR HU IE IL IQ IR IS IT JO KW
KZ LB LC LI LT LU LV LY MA MC MD ME MK ML MR MT MU MZ NE NI NL NO OM PK PL
PS PT QA RO RS SA SC SD SE SI SK SM SN SO ST SV TD TG TL TN TR UA VA VG XK
""".split())
_IBAN_PREFIX_RE = re.compile(r"(?<![A-Z0-9])([A-Z]{2}\d{2})", re.IGNORECASE)


def _has_valid_iban(text: str) -> bool:
    upper = str(text).upper()
    for prefix_match in _IBAN_PREFIX_RE.finditer(upper):
        prefix = prefix_match.group(1)
        if prefix[:2] not in _IBAN_COUNTRY_CODES:
            continue
        candidate_chars: list[str] = []
        for position in range(prefix_match.start(), min(len(upper), prefix_match.start() + 64)):
            char = upper[position]
            if char.isalnum():
                candidate_chars.append(char)
            elif char in " -":
                continue
            else:
                break
            size = len(candidate_chars)
            if not 15 <= size <= 34:
                continue
            next_char = upper[position + 1] if position + 1 < len(upper) else ""
            if next_char and next_char.isalnum():
                continue
            candidate = "".join(candidate_chars)
            rearranged = candidate[4:] + candidate[:4]
            remainder = 0
            for value in rearranged:
                if value.isdigit():
                    remainder = (remainder * 10 + int(value)) % 97
                else:
                    remainder = (remainder * 100 + ord(value) - 55) % 97
            if remainder == 1:
                return True
    return False



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
        # Explicit offline mode is a hard boundary: even configured credentials
        # must never cause a hosted request from the core conversation path.
        if preference in {"offline", "none", "disabled"}:
            return ()
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
            preference = self.environ.get("FINZANJIR_LLM_PROVIDER", "auto").strip().casefold()
            self.last_status = "offline_mode" if preference in {"offline", "none", "disabled"} else "not_configured"
            self.last_provider_failures = []
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
        # Conservative guard for common payment and identity identifiers before
        # any third-party model call. This is a deny-list, not full DLP coverage.
        if re.search(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)", text):
            return False
        if re.search(r"(?<!\w)[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}(?!\w)", text):
            return False
        if re.search(r"(?<!\d)\+?998[\s().-]?(?:\d[\s().-]?){9}(?!\d)", text):
            return False
        if re.search(r"(?<!\d)\+\d{1,3}(?:[\s().-]?\d){7,14}(?!\d)", text):
            return False
        if re.search(r"(?<![A-Z0-9])[A-Z]{2}[\s-]?\d{7}(?!\d)", text, flags=re.IGNORECASE):
            return False
        if _has_valid_iban(text):
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
