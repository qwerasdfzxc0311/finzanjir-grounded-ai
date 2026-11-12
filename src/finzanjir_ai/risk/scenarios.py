from __future__ import annotations

from typing import Any


def build_synthetic_case_signal_events(
    *,
    transaction_id: str,
    observed_at: str,
) -> list[dict[str, Any]]:
    """Build an explicit, clearly synthetic five-family case-review scenario.

    This helper is for deterministic demonstrations and tests only. It does not
    infer signals from amount or claim that any real bank event occurred.
    """
    if not isinstance(transaction_id, str) or not transaction_id.strip():
        raise ValueError("transaction_id must be a non-empty string")
    if not isinstance(observed_at, str) or not observed_at.strip():
        raise ValueError("observed_at must be a non-empty string")

    scenario = (
        ("SIG-018", "auth"),
        ("SIG-006", "device"),
        ("SIG-012", "account"),
        ("SIG-004", "beneficiary"),
        ("SIG-002", "velocity"),
    )
    return [
        {
            "signal_id": signal_id,
            "evidence_id": f"{transaction_id}:synthetic:{evidence_suffix}",
            "source": "synthetic-scenario-generator",
            "observed_at": observed_at,
            "evidence_quality": 1.0,
            "recency_factor": 1.0,
        }
        for signal_id, evidence_suffix in scenario
    ]
