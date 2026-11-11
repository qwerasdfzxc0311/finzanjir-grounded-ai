from __future__ import annotations

from dataclasses import dataclass
import hashlib
from itertools import combinations
from typing import Any


@dataclass(frozen=True)
class CrossBankMatchResult:
    matches: list[dict[str, Any]]
    graph_edges: list[dict[str, Any]]


class CrossBankMatcher:
    SHARED_KEYS = ("network_id", "device_id")

    def match(
        self,
        records: list[dict[str, Any]],
        *,
        scope: str,
        authorized_exchange: bool,
    ) -> CrossBankMatchResult:
        if scope != "cross_bank":
            raise ValueError("cross_bank scope is required")
        if not isinstance(authorized_exchange, bool):
            raise ValueError("authorized_exchange must be boolean")
        if not authorized_exchange:
            raise ValueError("authorized cross-bank exchange is required")

        matches: list[dict[str, Any]] = []
        graph_edges: list[dict[str, Any]] = []

        for key_type in self.SHARED_KEYS:
            grouped: dict[str, list[dict[str, Any]]] = {}
            for record in records:
                value = record.get(key_type)
                if isinstance(value, str) and value.strip():
                    grouped.setdefault(value, []).append(record)

            for raw_value, group in grouped.items():
                banks = {record.get("bank_id") for record in group}
                if len(banks) < 2:
                    continue

                correlation_hash = hashlib.sha256(raw_value.encode("utf-8")).hexdigest()
                for left, right in combinations(group, 2):
                    if left.get("bank_id") == right.get("bank_id"):
                        continue
                    matches.append({
                        "bank_id_a": left["bank_id"],
                        "transaction_id_a": left["transaction_id"],
                        "bank_id_b": right["bank_id"],
                        "transaction_id_b": right["transaction_id"],
                        "shared_key_type": key_type,
                        "correlation_key_hash": correlation_hash,
                        "scope": "cross_bank",
                    })
                    graph_edges.append({
                        "edge_type": "SHARED_NETWORK" if key_type == "network_id" else "SHARED_DEVICE",
                        "from": f"{left['bank_id']}:{left['transaction_id']}",
                        "to": f"{right['bank_id']}:{right['transaction_id']}",
                        "correlation_key_hash": correlation_hash,
                        "scope": "cross_bank",
                    })

        return CrossBankMatchResult(matches=matches, graph_edges=graph_edges)
