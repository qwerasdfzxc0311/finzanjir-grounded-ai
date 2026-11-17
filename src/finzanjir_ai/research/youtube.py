from __future__ import annotations

from urllib.parse import urlsplit
from typing import Any

_ALLOWED_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"}


def filter_youtube_video_results(payload: dict[str, Any]) -> dict[str, Any]:
    """Keep only HTTPS YouTube video URLs from a public web-search response."""
    results = payload.get("results", [])
    if not isinstance(results, list):
        results = []
    videos = []
    for item in results:
        if not isinstance(item, dict):
            continue
        try:
            parsed = urlsplit(str(item.get("url", "")))
        except ValueError:
            continue
        host = (parsed.hostname or "").lower()
        if parsed.scheme != "https" or host not in _ALLOWED_HOSTS:
            continue
        if host == "youtu.be":
            if not parsed.path.strip("/"):
                continue
        elif parsed.path != "/watch":
            continue
        videos.append({
            "title": str(item.get("title", "YouTube video"))[:300],
            "url": parsed.geturl(),
            "content": str(item.get("content", item.get("snippet", "")))[:2000],
            "score": item.get("score"),
        })
    return {
        "query": payload.get("query", ""),
        "results": videos,
        "source": "youtube_public_web_index",
        "note": "Natijalar ochiq indekslangan YouTube video sahifalaridir. Video to‘liq ko‘rilgani yoki transkript o‘qilgani anglatmaydi.",
    }
