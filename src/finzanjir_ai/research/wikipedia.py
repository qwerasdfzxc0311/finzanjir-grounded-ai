from __future__ import annotations

import html
import re
from typing import Any
from urllib.parse import quote

import httpx

from finzanjir_ai.answer.providers import LLMGateway
from finzanjir_ai.orchestration.intent import detect_query_language


class WikimediaSearchClient:
    """Keyless encyclopedia fallback for stable general-knowledge questions.

    Wikimedia is a separate provider from Tavily. It is not a general-purpose
    replacement for broad web search; it is used as a resilient source for
    encyclopedic topics when the primary search provider is unavailable.
    """

    API_URL = "https://{language}.wikipedia.org/w/api.php"
    USER_AGENT = (
        "FINZANJIR-GroundedAI/0.1 "
        "(https://github.com/qwerasdfzxc0311/finzanjir-grounded-ai)"
    )

    @staticmethod
    def _languages(query: str) -> tuple[str, ...]:
        language = detect_query_language(query)
        preferred = {
            "uz": ("uz", "en"),
            "ru": ("ru", "en"),
            "en": ("en",),
            "kk": ("kk", "ru", "en"),
            # Karakalpak coverage is less consistent; try its own project,
            # then Uzbek, Russian and English rather than silently translating.
            "kaa": ("kaa", "uz", "ru", "en"),
        }.get(language, ("en",))
        return tuple(dict.fromkeys(preferred))

    @staticmethod
    def _plain(value: Any, limit: int = 18000) -> str:
        text = html.unescape(str(value or ""))
        text = re.sub(r"<[^>]{1,500}>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:limit]

    def _get(self, language: str, params: dict[str, Any]) -> dict[str, Any]:
        response = httpx.get(
            self.API_URL.format(language=language),
            params=params,
            headers={"User-Agent": self.USER_AGENT, "Accept": "application/json"},
            timeout=httpx.Timeout(12.0, connect=4.0),
            follow_redirects=True,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("Invalid Wikimedia response")
        return payload

    def search(self, query: str, *, max_results: int = 5) -> dict[str, Any]:
        cleaned = str(query or "").strip()[:500]
        if not cleaned:
            raise ValueError("Search query must not be empty")
        if not LLMGateway.can_send_text(cleaned):
            raise ValueError("Search query contains a personal or payment identifier")

        limit = max(1, min(int(max_results), 6))
        last_error: Exception | None = None
        for language in self._languages(cleaned):
            try:
                search_payload = self._get(language, {
                    "action": "query",
                    "list": "search",
                    "srsearch": cleaned,
                    "srnamespace": 0,
                    "srlimit": limit,
                    "srprop": "snippet",
                    "format": "json",
                    "formatversion": 2,
                    "utf8": 1,
                })
                matches = search_payload.get("query", {}).get("search", [])
                titles = [
                    str(item.get("title", "")).strip()
                    for item in matches
                    if isinstance(item, dict) and item.get("title")
                ]
                if not titles:
                    continue

                extract_payload = self._get(language, {
                    "action": "query",
                    "prop": "extracts",
                    "exintro": 1,
                    "explaintext": 1,
                    "exsectionformat": "plain",
                    "redirects": 1,
                    "titles": "|".join(titles[:limit]),
                    "format": "json",
                    "formatversion": 2,
                    "utf8": 1,
                })
                pages = extract_payload.get("query", {}).get("pages", [])
                results: list[dict[str, Any]] = []
                for index, page in enumerate(pages[:limit]):
                    if not isinstance(page, dict) or page.get("missing"):
                        continue
                    title = str(page.get("title") or "").strip()
                    extract = self._plain(page.get("extract"))
                    if len(extract) < 80 or not title:
                        continue
                    snippet = self._plain(
                        next(
                            (
                                item.get("snippet")
                                for item in matches
                                if isinstance(item, dict) and item.get("title") == title
                            ),
                            "",
                        ),
                        limit=1200,
                    )
                    article_path = quote(title.replace(" ", "_"), safe="()!,:'")
                    results.append({
                        "title": title,
                        "url": f"https://{language}.wikipedia.org/wiki/{article_path}",
                        "snippet": snippet or extract[:1200],
                        "raw_content": extract[:18000],
                        "published_date": None,
                        "score": max(0.62, 0.84 - index * 0.04),
                    })
                if results:
                    return {
                        "source_type": "wikimedia_encyclopedia_fallback",
                        "query": cleaned,
                        "language": language,
                        "results": results,
                    }
            except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
                last_error = exc
                continue

        # Do not expose provider exception text or response bodies to callers.
        return {
            "source_type": "wikimedia_encyclopedia_fallback",
            "query": cleaned,
            "language": None,
            "results": [],
            "status": "unavailable" if last_error else "no_results",
        }
