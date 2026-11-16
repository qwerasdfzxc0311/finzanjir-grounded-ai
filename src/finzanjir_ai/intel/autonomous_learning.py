"""Policy-driven autonomous research cycle.

The scheduler is intentionally inert until explicitly enabled by the host.
It discovers from configured sources, stores evidence, and creates review
candidates; it never trains weights or publishes knowledge automatically.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
from typing import Callable, Iterable, Protocol
import json


class CandidateStatus(str, Enum):
    DISCOVERED = "discovered"
    FETCHED = "fetched"
    QUARANTINED = "quarantined"
    REVIEW_REQUIRED = "review_required"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass(frozen=True)
class ResearchSource:
    source_id: str
    domain: str
    category: str
    enabled: bool = False
    max_items_per_cycle: int = 10
    min_refresh_hours: int = 24
    allowed_content_types: tuple[str, ...] = ("text/plain", "text/html", "application/json")


@dataclass(frozen=True)
class ResearchCandidate:
    candidate_id: str
    source_id: str
    url: str
    title: str
    text: str
    content_hash: str
    discovered_at: str
    status: CandidateStatus
    review_reasons: tuple[str, ...] = ()


class DiscoveryAdapter(Protocol):
    def discover(self, source: ResearchSource, limit: int) -> Iterable[tuple[str, str]]:
        """Return (url, title) pairs; adapter must be read-only."""


class FetchAdapter(Protocol):
    def fetch(self, url: str) -> tuple[str, str, str]:
        """Return (text, content_type, canonical_url)."""


@dataclass
class AutonomousResearchPolicy:
    enabled: bool = False
    online_enabled: bool = False
    max_sources_per_cycle: int = 5
    max_items_per_cycle: int = 20
    max_bytes_per_item: int = 500_000
    max_total_bytes_per_cycle: int = 5_000_000
    cycle_interval_minutes: int = 360
    allowed_categories: tuple[str, ...] = (
        "official_advisory", "cve", "security_vendor", "academic_research",
        "public_science", "public_reference",
    )
    prohibited_terms: tuple[str, ...] = (
        "credential dump", "stolen credentials", "exploit kit download",
        "malware payload download", "illegal marketplace listing",
    )


class AutonomousResearchEngine:
    """Runs a bounded cycle and emits quarantined evidence candidates."""

    def __init__(self, policy: AutonomousResearchPolicy,
                 discoverer: DiscoveryAdapter, fetcher: FetchAdapter):
        self.policy = policy
        self.discoverer = discoverer
        self.fetcher = fetcher
        self._seen_hashes: set[str] = set()
        self._seen_urls: set[str] = set()

    def run_cycle(self, sources: Iterable[ResearchSource], *, offline: bool = False
                  ) -> list[ResearchCandidate]:
        if not self.policy.enabled:
            return []
        if not offline and not self.policy.online_enabled:
            return []

        output: list[ResearchCandidate] = []
        byte_budget = self.policy.max_total_bytes_per_cycle
        item_budget = self.policy.max_items_per_cycle
        enabled_sources = [
            s for s in sources
            if s.enabled and s.category in self.policy.allowed_categories
        ][:self.policy.max_sources_per_cycle]

        for source in enabled_sources:
            if item_budget <= 0 or byte_budget <= 0:
                break
            per_source = min(source.max_items_per_cycle, item_budget)
            for url, title in self.discoverer.discover(source, per_source):
                if item_budget <= 0 or byte_budget <= 0:
                    break
                if url in self._seen_urls:
                    continue
                self._seen_urls.add(url)
                try:
                    text, content_type, canonical_url = self.fetcher.fetch(url)
                except Exception:
                    # A failed source must not stop other sources in the cycle.
                    continue
                encoded = text.encode("utf-8", errors="replace")
                if content_type not in source.allowed_content_types:
                    continue
                if len(encoded) > min(self.policy.max_bytes_per_item, byte_budget):
                    continue
                byte_budget -= len(encoded)
                item_budget -= 1
                digest = sha256(encoded).hexdigest()
                if digest in self._seen_hashes:
                    continue
                self._seen_hashes.add(digest)
                lowered = (title + "\n" + text[:20000]).lower()
                reasons = ["external source content is untrusted; human review required"]
                if any(term in lowered for term in self.policy.prohibited_terms):
                    reasons.append("content matched a prohibited collection pattern")
                candidate_id = sha256(
                    (source.source_id + canonical_url + digest).encode()
                ).hexdigest()
                output.append(ResearchCandidate(
                    candidate_id=candidate_id, source_id=source.source_id,
                    url=canonical_url, title=title, text=text,
                    content_hash=digest,
                    discovered_at=datetime.now(timezone.utc).isoformat(),
                    status=CandidateStatus.QUARANTINED,
                    review_reasons=tuple(reasons),
                ))
        return output


@dataclass
class KnowledgePromotionGate:
    """Only reviewed, licensed, non-sensitive candidates can be promoted."""

    required_reviewers: int = 1
    approved_license_ids: set[str] = field(default_factory=set)

    def approve(self, candidate: ResearchCandidate, *, reviewer_ids: Iterable[str],
                license_id: str, contains_personal_data: bool = False,
                contains_customer_or_bank_data: bool = False,
                source_verified: bool = False) -> bool:
        reviewers = {item.strip() for item in reviewer_ids if item.strip()}
        if candidate.status != CandidateStatus.QUARANTINED:
            return False
        if len(reviewers) < self.required_reviewers:
            return False
        if not source_verified or license_id not in self.approved_license_ids:
            return False
        if contains_personal_data or contains_customer_or_bank_data:
            return False
        return True


def candidate_manifest(candidate: ResearchCandidate) -> str:
    """Serialize metadata only; source text is stored separately in quarantine."""
    return json.dumps({
        "candidate_id": candidate.candidate_id,
        "source_id": candidate.source_id,
        "url": candidate.url,
        "title": candidate.title,
        "content_hash": candidate.content_hash,
        "discovered_at": candidate.discovered_at,
        "status": candidate.status.value,
        "review_reasons": list(candidate.review_reasons),
    }, ensure_ascii=False, sort_keys=True)
