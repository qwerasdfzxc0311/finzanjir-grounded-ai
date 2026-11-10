from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CrossBankMatchResult:
    matches: tuple[tuple[str, str], ...]
    graph_edges: tuple[tuple[str, str], ...]
    scope: str = "cross_bank"


class CrossBankMatcher:
    def match(self, signals: list[dict[str, Any]], *, authorized: bool) -> CrossBankMatchResult:
        if not authorized:
            raise ValueError("cross-bank matching requires authorized exchange")

        grouped: dict[str, list[dict[str, Any]]] = {}
        for signal in signals:
            key = signal.get("correlation_key")
            bank_id = signal.get("bank_id")
            if not key or not bank_id:
                continue
            grouped.setdefault(str(key), []).append(signal)

        matches: list[tuple[str, str]] = []
        edges: list[tuple[str, str]] = []
        for group in grouped.values():
            for index, left in enumerate(group):
                for right in group[index + 1 :]:
                    if left["bank_id"] == right["bank_id"]:
                        continue
                    pair = tuple(sorted((str(left["id"]), str(right["id"]))))
                    matches.append(pair)
                    edges.append((f"{left['bank_id']}:{left['id']}", f"{right['bank_id']}:{right['id']}"))

        return CrossBankMatchResult(
            matches=tuple(sorted(set(matches))),
            graph_edges=tuple(sorted(set(edges))),
        )
