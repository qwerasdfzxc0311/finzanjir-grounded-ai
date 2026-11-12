from __future__ import annotations

from typing import Any, Iterable


class TransactionChainCorrelator:
    """Correlate transaction events while preserving proof-completeness boundaries."""

    REQUIRED_METADATA = ("source", "occurred_at", "correlation_reason")

    def correlate(
        self,
        events: Iterable[dict[str, Any]],
        *,
        allow_incomplete: bool = False,
    ) -> dict[str, Any]:
        normalized = [dict(event) for event in events]

        if not normalized:
            raise ValueError("Transaction chain requires at least one event")

        incomplete_event_ids: list[str] = []
        for index, event in enumerate(normalized):
            event_id = event.get("event_id") or f"event-{index + 1}"
            missing = [
                field
                for field in self.REQUIRED_METADATA
                if not isinstance(event.get(field), str) or not event[field].strip()
            ]
            if missing:
                if not allow_incomplete:
                    raise ValueError(
                        f"Transaction chain event {event_id} is missing {missing[0]}"
                    )
                incomplete_event_ids.append(event_id)

        transaction_ids = {
            event.get("transaction_id")
            for event in normalized
            if isinstance(event.get("transaction_id"), str) and event["transaction_id"].strip()
        }
        complete = not incomplete_event_ids and len(transaction_ids) == 1
        if len(transaction_ids) != 1:
            complete = False

        if not complete and not allow_incomplete:
            raise ValueError("Transaction chain is incomplete")

        return {
            "complete": complete,
            "final_proof": complete,
            "events": normalized,
            "incomplete_event_ids": incomplete_event_ids,
        }
