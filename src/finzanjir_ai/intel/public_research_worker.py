"""Bounded public-web research worker for the autonomous cycle supervisor.

It uses Tavily's provider-side fetch/extract result rather than connecting to
arbitrary result URLs from the worker host. Results are untrusted and quarantined.
"""
from __future__ import annotations

from datetime import datetime, timezone
import ipaddress
import re
from hashlib import sha256
from typing import Any
from urllib.parse import urlsplit

from finzanjir_ai.intel.autonomous_learning import CandidateStatus, ResearchCandidate
from finzanjir_ai.intel.cycle_supervisor import WorkStep
from finzanjir_ai.intel.runtime_store import LocalResearchRuntimeStore
from finzanjir_ai.research.tavily import TavilySearchClient


MAX_RESULTS_PER_CYCLE = 8
MAX_BYTES_PER_ITEM = 500_000
MAX_TOTAL_BYTES_PER_CYCLE = 5_000_000


def _host_allowed(url: str, allowed_domains: tuple[str, ...]) -> bool:
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError:
        return False
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        return False
    if port not in (None, 443):
        return False
    host = parsed.hostname.lower().rstrip(".")
    return any(host == domain or host.endswith("." + domain) for domain in allowed_domains)


def build_public_research_worker(
    *,
    source_id: str,
    query: str,
    allowed_domains: list[str] | tuple[str, ...],
    store: LocalResearchRuntimeStore,
    search_client: TavilySearchClient | None = None,
):
    cleaned_query = query.strip()
    if not source_id.strip() or not cleaned_query or len(cleaned_query) > 500:
        raise ValueError("source_id and a 1-500 character query are required")
    domains = tuple(sorted({
        str(domain).strip().lower().rstrip(".")
        for domain in allowed_domains if str(domain).strip()
    }))
    common_public_suffixes = {
        "com", "org", "net", "edu", "gov", "mil", "int", "io", "dev", "app",
        "co.uk", "org.uk", "gov.uk", "ac.uk", "com.au", "net.au", "org.au",
        "co.jp", "com.br", "com.cn", "com.in",
    }
    def valid_domain(domain: str) -> bool:
        if domain in common_public_suffixes:
            return False
        if not re.fullmatch(
            r"(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\\.)+[a-z]{2,63}",
            domain,
        ):
            return False
        try:
            ipaddress.ip_address(domain)
        except ValueError:
            return True
        return False

    if not domains or any(not valid_domain(domain) for domain in domains):
        raise ValueError(
            "allowlist must contain exact DNS domains, not URLs, IPs, wildcards or public suffixes"
        )
    search = search_client or TavilySearchClient()

    async def worker(checkpoint: dict[str, Any], remaining_seconds: float) -> WorkStep:
        if checkpoint:
            raise ValueError("this worker uses idempotent single-batch checkpoints only")
        response = search.search(
            cleaned_query, max_results=MAX_RESULTS_PER_CYCLE, include_raw_content=True
        )
        saved = 0
        total_bytes = 0
        skipped = 0
        for item in response.get("results", [])[:MAX_RESULTS_PER_CYCLE]:
            url = str(item.get("url") or "")
            if not _host_allowed(url, domains):
                skipped += 1
                continue
            text = str(item.get("raw_content") or item.get("snippet") or "").strip()
            if not text:
                skipped += 1
                continue
            encoded = text.encode("utf-8", errors="replace")
            if len(encoded) > MAX_BYTES_PER_ITEM or total_bytes + len(encoded) > MAX_TOTAL_BYTES_PER_CYCLE:
                skipped += 1
                continue
            digest = sha256(encoded).hexdigest()
            title = str(item.get("title") or "Untitled public source")[:300]
            candidate_id = sha256(
                (source_id + url + digest).encode()
            ).hexdigest()
            candidate = ResearchCandidate(
                candidate_id=candidate_id,
                source_id=source_id,
                url=url,
                title=title,
                text=text,
                content_hash=digest,
                discovered_at=datetime.now(timezone.utc).isoformat(),
                status=CandidateStatus.QUARANTINED,
                review_reasons=(
                    "External source extract is untrusted; human source/licence review required.",
                    "Content was supplied by the search provider and was not fetched directly by FINZANJIR.",
                ),
            )
            store.save_candidate(candidate, source_mode="online")
            saved += 1
            total_bytes += len(encoded)

        return WorkStep(
            {},
            done=True,
            items=saved,
            bytes_processed=total_bytes,
            detail=f"Research batch saved {saved} candidate(s) to quarantine; {skipped} result(s) skipped.",
        )

    return worker
