from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import random
from typing import Any

from finzanjir_ai.contracts.event_validation import build_event_envelope


@dataclass
class SyntheticBank:
    seed: int = 0
    bank_id: str = "bank-demo"

    def __post_init__(self) -> None:
        self._rng = random.Random(self.seed)
        self._counter = 0

    def generate_transactions(self, count: int) -> list[dict[str, Any]]:
        if count < 0:
            raise ValueError("count must be non-negative")
        transactions: list[dict[str, Any]] = []
        base_time = datetime(2026, 11, 11, tzinfo=timezone.utc)
        for _ in range(count):
            self._counter += 1
            transaction_id = f"syn-tx-{self.bank_id}-{self._counter:06d}"
            actor_id = f"syn-actor-{self._rng.randint(1, 9999):04d}"
            amount = round(self._rng.uniform(5, 5000), 2)
            occurred_at = base_time + timedelta(seconds=self._counter)
            transactions.append({
                "id": transaction_id,
                "transaction_id": transaction_id,
                "bank_id": self.bank_id,
                "actor_id": actor_id,
                "amount": amount,
                "currency": "UZS",
                "occurred_at": occurred_at.isoformat().replace("+00:00", "Z"),
                "channel": self._rng.choice(["card", "mobile", "web", "atm"]),
                "status": "AUTHORIZED",
                "synthetic": True,
            })
        return transactions

    def generate_transaction_events(self, count: int) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        for transaction in self.generate_transactions(count):
            events.append(build_event_envelope(
                event_id=f"evt-{transaction['id']}",
                event_type="TransactionObserved",
                occurred_at=transaction["occurred_at"],
                actor_id=transaction["actor_id"],
                scope="bank_internal",
                object_type="Transaction",
                object_id=transaction["id"],
                payload=transaction,
            ))
        return events


def generate_synthetic_batch(*, seed: int = 0, count: int = 1, bank_id: str = "bank-demo") -> list[dict[str, Any]]:
    return SyntheticBank(seed=seed, bank_id=bank_id).generate_transactions(count)
