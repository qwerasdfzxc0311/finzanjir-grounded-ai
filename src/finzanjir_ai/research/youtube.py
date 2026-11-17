from __future__ import annotations

import re
from urllib.parse import parse_qs, urlsplit
from typing import Any

_ALLOWED_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"}
_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{3,20}$")


def _video_id(url) -> str | None:
    try:
        parsed = urlsplit(str(url or ""))
    except ValueError:
        return None
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or host not in _ALLOWED_HOSTS:
        return None
    if host == "youtu.be":
        candidate = parsed.path.strip("/").split("/", 1)[0]
    else:
        if parsed.path != "/watch":
            return None
        candidate = (parse_qs(parsed.query).get("v") or [""])[0]
    candidate = str(candidate).strip()
    return candidate if _VIDEO_ID_RE.fullmatch(candidate) else None


def filter_youtube_video_results(payload: dict[str, Any]) -> dict[str, Any]:
    """Keep unique HTTPS YouTube videos, stripping tracking parameters."""
    results = payload.get("results", [])
    if not isinstance(results, list):
        results = []

    candidates = []
    for position, item in enumerate(results):
        if not isinstance(item, dict):
            continue
        video_id = _video_id(item.get("url"))
        if not video_id:
            continue
        score = item.get("score")
        candidates.append({
            "video_id": video_id,
            "title": str(item.get("title") or "YouTube video")[:300],
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "content": str(item.get("content", item.get("snippet", "")))[:2000],
            "score": score,
            "_position": position,
        })

    candidates.sort(
        key=lambda item: (
            item["score"] if isinstance(item.get("score"), (int, float)) else 0,
            -item["_position"],
        ),
        reverse=True,
    )
    videos = []
    seen_ids: set[str] = set()
    for item in candidates:
        if item["video_id"] in seen_ids:
            continue
        seen_ids.add(item["video_id"])
        item.pop("video_id", None)
        item.pop("_position", None)
        videos.append(item)

    return {
        "query": payload.get("query", ""),
        "results": videos,
        "source": "youtube_public_web_index",
        "note": "Natijalar ochiq indekslangan YouTube video sahifalaridir. Video to‘liq ko‘rilgani yoki transkript o‘qilgani anglatmaydi.",
    }
