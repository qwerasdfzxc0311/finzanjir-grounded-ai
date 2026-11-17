from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
import hashlib
import threading
import time
from typing import Any

from finzanjir_ai.answer.providers import LLMGateway


class PublicResearchCache:
    """Small bounded in-process cache containing only public-source extracts."""

    def __init__(self, *, ttl_seconds: int = 6 * 60 * 60, max_entries: int = 128) -> None:
        self.ttl_seconds = max(60, int(ttl_seconds))
        self.max_entries = max(1, int(max_entries))
        self._items: OrderedDict[str, tuple[float, dict[str, Any]]] = OrderedDict()
        self._lock = threading.Lock()

    @staticmethod
    def _key(query: str) -> str:
        normalized = " ".join(str(query or "").casefold().split())
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def get(self, query: str) -> dict[str, Any] | None:
        if not LLMGateway.can_send_text(query):
            return None
        key = self._key(query)
        now = time.monotonic()
        with self._lock:
            entry = self._items.get(key)
            if entry is None:
                return None
            expires_at, payload = entry
            if expires_at <= now:
                self._items.pop(key, None)
                return None
            self._items.move_to_end(key)
            return deepcopy(payload)

    def put(self, query: str, provider: str, results: list[dict[str, Any]]) -> None:
        if not results or not LLMGateway.can_send_text(query):
            return
        key = self._key(query)
        payload = {
            "provider": str(provider),
            "results": deepcopy(results[:8]),
        }
        with self._lock:
            self._items[key] = (time.monotonic() + self.ttl_seconds, payload)
            self._items.move_to_end(key)
            while len(self._items) > self.max_entries:
                self._items.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._items.clear()


class ProviderCooldown:
    """Per-process circuit breaker to stop retrying a quota-limited provider."""

    def __init__(self) -> None:
        self._until = 0.0
        self._status = "ready"
        self._lock = threading.Lock()

    def is_open(self) -> bool:
        with self._lock:
            if self._until <= time.monotonic():
                self._status = "ready"
                self._until = 0.0
                return False
            return True

    def status(self) -> str:
        with self._lock:
            if self._until <= time.monotonic():
                return "ready"
            return self._status

    def record_success(self) -> None:
        with self._lock:
            self._until = 0.0
            self._status = "ready"

    def record_failure(self, status: str) -> int:
        cooldown = {
            "rate_limited": 15 * 60,
            "quota_exhausted": 30 * 60,
            "authentication_or_permission_failed": 30 * 60,
            "provider_unavailable": 60,
            "network_error": 60,
        }.get(status, 60)
        with self._lock:
            self._until = time.monotonic() + cooldown
            self._status = status
        return cooldown

    def remaining_seconds(self) -> int:
        with self._lock:
            return max(0, int(self._until - time.monotonic()))
