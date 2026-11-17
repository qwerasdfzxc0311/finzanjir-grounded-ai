from __future__ import annotations

import os
from typing import Any, Literal

import httpx

from finzanjir_ai.answer.providers import LLMGateway


class TavilySearchClient:
    """External web research adapter kept separate from the canonical FINZANJIR KB."""

    ENDPOINT = "https://api.tavily.com/search"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key if api_key is not None else os.getenv("TAVILY_API_KEY")

    def search(
        self,
        query: str,
        *,
        max_results: int = 5,
        include_raw_content: bool = False,
        search_depth: Literal["basic", "advanced"] = "advanced",
        topic: Literal["general", "news"] = "general",
        time_range: Literal["day", "week", "month", "year"] | None = None,
    ) -> dict[str, Any]:
        cleaned = str(query).strip()
        if not cleaned:
            raise ValueError("Search query must not be empty")
        if not LLMGateway.can_send_text(cleaned):
            raise ValueError("Search query contains a personal or payment identifier")
        if not self.api_key:
            raise RuntimeError("External research is not configured")
        if search_depth not in {"basic", "advanced"}:
            raise ValueError("Unsupported search depth")
        if topic not in {"general", "news"}:
            raise ValueError("Unsupported search topic")
        if time_range is not None and time_range not in {"day", "week", "month", "year"}:
            raise ValueError("Unsupported time range")

        payload: dict[str, Any] = {
            "query": cleaned[:500],
            "topic": topic,
            "search_depth": search_depth,
            "max_results": max(1, min(int(max_results), 8)),
            "include_answer": False,
            "include_raw_content": bool(include_raw_content),
        }
        if time_range:
            payload["time_range"] = time_range

        response = httpx.post(
            self.ENDPOINT,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=httpx.Timeout(25.0, connect=5.0),
        )
        response.raise_for_status()
        body = response.json()
        results = []
        seen_urls: set[str] = set()
        for item in body.get("results", [])[:8]:
            if not isinstance(item, dict) or not item.get("url"):
                continue
            url = str(item["url"])[:2000]
            if url in seen_urls:
                continue
            seen_urls.add(url)
            results.append({
                "title": str(item.get("title") or "Untitled source")[:300],
                "url": url,
                "snippet": str(item.get("content") or "")[:1800],
                "raw_content": str(item.get("raw_content") or "")[:500_000] if include_raw_content else "",
                "published_date": item.get("published_date"),
                "score": item.get("score"),
            })
        results.sort(
            key=lambda item: item["score"] if isinstance(item.get("score"), (int, float)) else 0,
            reverse=True,
        )
        return {
            "source_type": "external_web_research",
            "query": cleaned[:500],
            "topic": topic,
            "search_depth": search_depth,
            "time_range": time_range,
            "results": results[: max(1, min(int(max_results), 8))],
            "warning": (
                "Bu tashqi internet manbalari. Ular FINZANJIRning tasdiqlangan bilimlar bazasi emas "
                "va loyiha fakti sifatida avtomatik qabul qilinmaydi."
            ),
        }
