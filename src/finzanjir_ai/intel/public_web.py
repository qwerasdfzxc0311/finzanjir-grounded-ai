"""Safe, allowlisted public-web evidence retrieval with an offline cache.

This module is deliberately read-only. It never submits user content, follows
redirects, executes downloaded content, or accesses onion services.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from ipaddress import ip_address
from pathlib import Path
from typing import Iterable
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
import json
import socket
import sqlite3


MAX_RESPONSE_BYTES = 1_000_000
DEFAULT_TIMEOUT_SECONDS = 8


class WebIntelError(ValueError):
    """Raised when a request violates the safe retrieval policy."""


@dataclass(frozen=True)
class EvidenceRecord:
    url: str
    domain: str
    retrieved_at: str
    content_type: str
    text: str
    sha256: str
    source_mode: str = "online"


def _host_is_public(host: str) -> bool:
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(host, None)}
    except OSError as exc:
        raise WebIntelError("Host could not be resolved") from exc
    if not addresses:
        return False
    for raw in addresses:
        address = ip_address(raw.split("%", 1)[0])
        if not address.is_global:
            return False
    return True


def _domain_allowed(host: str, allowed_domains: Iterable[str]) -> bool:
    host = host.lower().rstrip(".")
    return any(host == domain.lower().strip(".") or
               host.endswith("." + domain.lower().strip("."))
               for domain in allowed_domains)


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise WebIntelError("Redirects are disabled; validate the new source separately")


class OfflineEvidenceStore:
    """Small SQLite cache; reads work without network access."""

    def __init__(self, path: str | Path):
        self.path = str(path)
        with sqlite3.connect(self.path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS evidence (
                url TEXT PRIMARY KEY, domain TEXT NOT NULL, retrieved_at TEXT NOT NULL,
                content_type TEXT NOT NULL, text TEXT NOT NULL, digest TEXT NOT NULL
            )""")

    def put(self, record: EvidenceRecord) -> None:
        with sqlite3.connect(self.path) as db:
            db.execute(
                "INSERT OR REPLACE INTO evidence VALUES (?, ?, ?, ?, ?, ?)",
                (record.url, record.domain, record.retrieved_at,
                 record.content_type, record.text, record.sha256),
            )

    def get(self, url: str) -> EvidenceRecord | None:
        with sqlite3.connect(self.path) as db:
            row = db.execute(
                "SELECT url, domain, retrieved_at, content_type, text, digest "
                "FROM evidence WHERE url = ?", (url,)
            ).fetchone()
        if row is None:
            return None
        return EvidenceRecord(*row, source_mode="offline_cache")


class PublicWebIntelClient:
    """Fetch public HTTPS text from explicitly approved domains only."""

    def __init__(self, allowed_domains: Iterable[str] = (), timeout: int = DEFAULT_TIMEOUT_SECONDS,
                 max_bytes: int = MAX_RESPONSE_BYTES, cache: OfflineEvidenceStore | None = None):
        self.allowed_domains = tuple(d.lower().strip(".") for d in allowed_domains if d.strip())
        self.timeout = max(1, min(int(timeout), 20))
        self.max_bytes = max(1, min(int(max_bytes), MAX_RESPONSE_BYTES))
        self.cache = cache

    def fetch(self, url: str, *, offline: bool = False) -> EvidenceRecord:
        parsed = urlsplit(url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise WebIntelError("Only absolute HTTPS URLs are accepted")
        if parsed.username or parsed.password or parsed.port not in (None, 443):
            raise WebIntelError("Credentials and non-standard ports are not accepted")
        host = parsed.hostname.lower().rstrip(".")
        if not _domain_allowed(host, self.allowed_domains):
            raise WebIntelError("Domain is not in the explicit allowlist")
        if offline:
            cached = self.cache.get(url) if self.cache else None
            if cached is None:
                raise WebIntelError("No cached evidence is available for this URL")
            return cached
        if not _host_is_public(host):
            raise WebIntelError("Private, local, or non-global network destinations are blocked")

        request = Request(url, headers={
            "User-Agent": "FINZANJIR-Research/1.0 (read-only; contact: project maintainer)",
            "Accept": "text/plain,text/html,application/json",
        }, method="GET")
        opener = build_opener(_NoRedirect())
        try:
            with opener.open(request, timeout=self.timeout) as response:
                content_type = response.headers.get_content_type().lower()
                if content_type not in {"text/plain", "text/html", "application/json"}:
                    raise WebIntelError("Only plain text, HTML, and JSON are accepted")
                raw = response.read(self.max_bytes + 1)
                if len(raw) > self.max_bytes:
                    raise WebIntelError("Response exceeds the configured size limit")
                charset = response.headers.get_content_charset() or "utf-8"
                text = raw.decode(charset, errors="replace")
        except (URLError, TimeoutError, OSError) as exc:
            raise WebIntelError("Public source could not be retrieved") from exc

        record = EvidenceRecord(
            url=url, domain=host, retrieved_at=datetime.now(timezone.utc).isoformat(),
            content_type=content_type, text=text, sha256=sha256(raw).hexdigest(),
        )
        if self.cache:
            self.cache.put(record)
        return record
