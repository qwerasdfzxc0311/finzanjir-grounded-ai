from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from typing import Any

from finzanjir_ai.contracts.event_validation import build_event_envelope


SCENARIOS = {"normal", "suspicious"}


def generate_demo_scenario(*, seed: int, scenario: str) -> dict[str, Any]:
    if scenario not in SCENARIOS:
        raise ValueError(f"Unknown synthetic scenario: {scenario}")

    rng = random.Random(seed)
    suffix = f"{seed:06d}"

    bank = {
        "id": f"bank-syn-{suffix}",
        "name": f"Synthetic Bank {rng.randint(10, 99)}",
        "synthetic": True,
    }
    actor = {
        "id": f"actor-syn-{suffix}",
        "type": "customer",
        "synthetic": True,
    }
    card = {
        "id": f"card-syn-{suffix}",
        "actor_id": actor["id"],
        "bank_id": bank["id"],
        "synthetic": True,
    }
    device = {
        "id": f"device-syn-{suffix}",
        "actor_id": actor["id"],
        "channel": "mobile",
        "synthetic": True,
    }
    network = {
        "id": f"network-syn-{suffix}",
        "ip_address": f"198.51.100.{rng.randint(10, 240)}",
        "device_id": device["id"],
        "synthetic": True,
    }

    amount = (
        rng.randint(100_001, 250_000)
        if scenario == "suspicious"
        else rng.randint(1_000, 50_000)
    )
    occurred_at = (
        datetime(2026, 11, 11, tzinfo=timezone.utc)
        + timedelta(seconds=rng.randint(0, 86_399))
    ).isoformat().replace("+00:00", "Z")

    transaction = {
        "id": f"txn-syn-{suffix}",
        "bank_id": bank["id"],
        "actor_id": actor["id"],
        "card_id": card["id"],
        "device_id": device["id"],
        "network_id": network["id"],
        "ip_address": network["ip_address"],
        "occurred_at": occurred_at,
        "amount": amount,
        "currency": "UZS",
        "channel": "mobile",
        "synthetic": True,
    }

    event = build_event_envelope(
        event_id=f"evt-syn-{suffix}",
        event_type="TransactionObserved",
        occurred_at=occurred_at,
        actor_id="synthetic-generator",
        scope="bank_internal",
        object_type="Transaction",
        object_id=transaction["id"],
        payload=transaction,
    )

    return {
        "synthetic": True,
        "scenario": scenario,
        "expected_escalation": scenario == "suspicious",
        "bank": bank,
        "actor": actor,
        "card": card,
        "device": device,
        "network": network,
        "transaction": transaction,
        "event": event,
    }
