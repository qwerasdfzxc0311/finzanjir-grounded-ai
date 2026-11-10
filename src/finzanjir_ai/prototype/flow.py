from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SystemFlow:
    """One shared prototype flow rendered as separate, connected work windows."""

    window_ids: tuple[str, ...]
    transitions: tuple[tuple[str, str], ...]
    architecture_layers: int = 16

    def trace(self, transaction_id: str) -> list[dict[str, Any]]:
        """Return a deterministic trace with one transaction identity across every window."""
        steps: list[dict[str, Any]] = []
        shared = {
            "transaction_id": transaction_id,
            "architecture_layers": self.architecture_layers,
            "data_mode": "synthetic",
        }
        for index, window_id in enumerate(self.window_ids):
            step = dict(shared)
            step["window_id"] = window_id
            step["sequence"] = index + 1
            if window_id == "cross_bank_fraud":
                step["scope"] = "cross_bank"
                step["authorized_exchange"] = True
            steps.append(step)
        return steps


def build_system_flow() -> SystemFlow:
    window_ids = (
        "synthetic_bank",
        "signal_risk",
        "human_case",
        "cross_bank_fraud",
        "audit_kpi",
        "finzanjir_ai",
        "citizen",
        "layers_16",
    )
    transitions = tuple(zip(window_ids, window_ids[1:]))
    return SystemFlow(window_ids=window_ids, transitions=transitions)
