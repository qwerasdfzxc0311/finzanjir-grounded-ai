"""Bounded public-web research worker for the autonomous cycle supervisor.

Only operator-configured public research topics and exact domain allowlists are used.
The worker stores candidates in quarantine and never promotes them to the KB.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from typing import Any
from urllib.parse import urlsplit

from finzanjir_ai.intel.autonomous_learning import CandidateStatus, ResearchCandidate
from finzanjir_ai.intel.cycle_supervisor import WorkStep
from finzanjir_ai.intel.public_web import PublicWebIntelClient
from finzanjir_ai.intel.runtime_store import LocalResearchRuntimeStore
from finzanjir_ai.research.tavily import TavilySearchClient


def _host_allowed(url: str, allowed_domains: tuple[str, ...]) -> bool:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        return False
    host = parsed.hostname.lower().rstrip(".")
    if parsed.port not in (None, 443):
        return False
    return any(
        host == domain or host.endswith("." + domain)
        for domain in allowed_domains
    )


def build_public_research_worker(
    *,
    source_id: str,
    query: str,
    allowed_domains: list[str] | tuple[str, ...],
    store: LocalResearchRuntimeStore,
    search_client: TavilySearchClient | None = None,
    fetch_client: PublicWebIntelClient | None = None,
):
    cleaned_query = query.strip()
    if not source_id.strip() or not cleaned_query or len(cleaned_query) > 500:
        raise ValueError("source_id and a 1-500 character query are required")
    domains = tuple(sorted({
        str(domain).strip().lower().strip(".")
        for domain in allowed_domains if str(domain).strip()
    }))
    if not domains or any("/" in domain or ":" in domain or "@" in domain for domain in domains):
        raise ValueError("one or more exact public domains must be allowlisted")
    search = search_client or TavilySearchClient()
    fetch = fetch_client or PublicWebIntelClient(allowed_domains=domains)

    async def worker(checkpoint: dict[str, Any], remaining_seconds: float) -> WorkStep:
        if not checkpoint:
            response = search.search(cleaned_query, max_results=8)
            results = []
            for item in response.get("results", [])[:8]:
                url = str(item.get("url") or "")
                if _host_allowed(url, domains):
                    results.append({
                        "url": url,
                        "title": str(item.get("title") or "Untitled public source")[:300],
                    })
            next_checkpoint = {"query": cleaned_query, "results": results, "cursor": 0}
            return WorkStep(
                next_checkpoint,
                done=not results,
                detail=f"Public search found {len(results)} allowlisted candidate URLs.",
            )

        results = checkpoint.get("results", [])
        cursor = int(checkpoint.get("cursor", 0))
        if cursor >= len(results):
            return WorkStep({}, done=True, detail="All allowlisted results in this search batch were processed.")

        item = results[cursor]
        url = str(item.get("url") or "")
        title = str(item.get("title") or "Untitled public source")
        saved = 0
        processed_bytes = 0
        detail = "Source could not be safely fetched; skipped."
        if _host_allowed(url, domains):
            try:
                evidence = fetch.fetch(url)
                text = evidence.text[:500_000]
                encoded = text.encode("utf-8")
                digest = sha256(encoded).hexdigest()
                canonical_url = evidence.url
                candidate_id = sha256(
                    (source_id + canonical_url + digest).encode()
                ).hexdigest()
                candidate = ResearchCandidate(
                    candidate_id=candidate_id,
                    source_id=source_id,
                    url=canonical_url,
                    title=title,
                    text=text,
                    content_hash=digest,
                    discovered_at=datetime.now(timezone.utc).isoformat(),
                    status=CandidateStatus.QUARANTINED,
                    review_reasons=(
                        "External public source is untrusted; owner review required.",
                    ),
                )
                store.save_candidate(candidate, source_mode="online")
                saved = 1
                processed_bytes = len(encoded)
                detail = "Public source fetched and saved to quarantine; no automatic promotion."
            except Exception as exc:
                detail = "Public source skipped after safe-fetch error: " + type(exc).__name__

        next_cursor = cursor + 1
        done = next_cursor >= len(results)
        next_checkpoint = {} if done else {
            "query": cleaned_query, "results": results, "cursor": next_cursor,
        }
        return WorkStep(
            next_checkpoint, done=done, items=saved,
            bytes_processed=processed_bytes, detail=detail,
        )

    return worker
