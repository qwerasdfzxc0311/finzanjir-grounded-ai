from __future__ import annotations

import os
from typing import Any

import httpx

from finzanjir_ai.answer.providers import LLMGateway


class TavilySearchClient:
    """External web research adapter kept separate from the canonical FINZANJIR KB."""

    ENDPOINT = "https://api.tavily.com/search"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key if api_key is not None else os.getenv("TAVILY_API_KEY")

    def search(self, query: str, *, max_results: int = 5, include_raw_content: bool = False) -> dict[str, Any]:
        cleaned = str(query).strip()
        if not cleaned:
            raise ValueError("Search query must not be empty")
        if not LLMGateway.can_send_text(cleaned):
            raise ValueError("Search query contains a personal or payment identifier")
        if not self.api_key:
            raise RuntimeError("External research is not configured")

        response = httpx.post(
            self.ENDPOINT,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={
                "query": cleaned[:500],
                "topic": "general",
                "search_depth": "basic",
                "max_results": max(1, min(int(max_results), 8)),
                "include_answer": False,
                "include_raw_content": bool(include_raw_content),
            },
            timeout=httpx.Timeout(18.0, connect=5.0),
        )
        response.raise_for_status()
        body = response.json()
        results = []
        for item in body.get("results", [])[:8]:
            if not isinstance(item, dict) or not item.get("url"):
                continue
            results.append({
                "title": str(item.get("title") or "Untitled source")[:300],
                "url": str(item["url"])[:2000],
                "snippet": str(item.get("content") or "")[:1800],
                "raw_content": str(item.get("raw_content") or "")[:500_000] if include_raw_content else "",
                "published_date": item.get("published_date"),
                "score": item.get("score"),
            })
        return {
            "source_type": "external_web_research",
            "query": cleaned[:500],
            "results": results,
            "warning": (
                "Bu tashqi internet manbalari. Ular FINZANJIRning tasdiqlangan bilimlar bazasi emas "
                "va loyiha fakti sifatida avtomatik qabul qilinmaydi."
            ),
        }
