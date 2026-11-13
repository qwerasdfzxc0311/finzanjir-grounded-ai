from __future__ import annotations

from datetime import datetime
import re
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


    SYNTHETIC_EVENT_FIELDS = frozenset({
        "event_id", "transaction_id", "source", "occurred_at",
        "correlation_reason", "data_mode",
    })
    SYNTHETIC_LINK_FIELDS = frozenset({
        "link_id", "from_transaction_id", "to_transaction_id",
        "relation_type", "source", "occurred_at", "correlation_reason",
        "data_mode",
    })
    ALLOWED_RELATION_TYPES = frozenset({
        "TRANSFER", "SEQUENCE", "ASSOCIATION", "CASE_REFERENCE",
    })
    OPAQUE_ID_PATTERN = re.compile(r"[A-Za-z0-9._:-]{1,128}")

    @classmethod
    def _synthetic_id(cls, value: Any, field: str) -> str:
        if not isinstance(value, str) or not cls.OPAQUE_ID_PATTERN.fullmatch(value.strip()):
            raise ValueError(f"{field} must be a 1-128 character opaque identifier")
        return value.strip()

    @staticmethod
    def _synthetic_time(value: Any, field: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field} must be a non-empty ISO-8601 timestamp")
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"{field} must be ISO-8601") from exc
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError(f"{field} must include a timezone")
        return value.strip()

    def correlate_synthetic_graph(
        self,
        events: Iterable[dict[str, Any]],
        links: Iterable[dict[str, Any]],
        *,
        allow_incomplete: bool = False,
    ) -> dict[str, Any]:
        """Build a synthetic-only transaction graph; connectivity is not proof of fraud."""
        if not isinstance(allow_incomplete, bool):
            raise ValueError("allow_incomplete must be boolean")
        if isinstance(events, (str, bytes, dict)) or isinstance(links, (str, bytes, dict)):
            raise ValueError("events and links must be iterables of objects")
        try:
            normalized_events = list(events)
            normalized_links = list(links)
        except TypeError as exc:
            raise ValueError("events and links must be iterable") from exc
        if not normalized_events:
            raise ValueError("Synthetic transaction graph requires at least one event")

        event_ids: set[str] = set()
        transaction_ids: set[str] = set()
        incomplete_event_ids: list[str] = []
        safe_events: list[dict[str, str]] = []

        for index, event in enumerate(normalized_events):
            if not isinstance(event, dict):
                raise ValueError(f"events[{index}] must be an object")
            extra = set(event) - self.SYNTHETIC_EVENT_FIELDS
            if extra:
                raise ValueError(f"events[{index}] contains unsupported fields: {', '.join(sorted(extra))}")
            event_id = self._synthetic_id(event.get("event_id"), f"events[{index}].event_id")
            transaction_id = self._synthetic_id(event.get("transaction_id"), f"events[{index}].transaction_id")
            if event_id in event_ids:
                raise ValueError(f"duplicate event_id: {event_id}")
            event_ids.add(event_id)
            transaction_ids.add(transaction_id)

            missing: list[str] = []
            for field in ("source", "occurred_at", "correlation_reason"):
                value = event.get(field)
                if not isinstance(value, str) or not value.strip():
                    missing.append(field)
            if event.get("data_mode") != "synthetic":
                missing.append("data_mode=synthetic")
            if missing and not allow_incomplete:
                raise ValueError(f"event {event_id} is incomplete: {missing[0]}")

            safe_event = {
                "event_id": event_id,
                "transaction_id": transaction_id,
                "data_mode": "synthetic",
            }
            if not missing:
                safe_event.update({
                    "source": event["source"].strip(),
                    "occurred_at": self._synthetic_time(event["occurred_at"], f"events[{index}].occurred_at"),
                    "correlation_reason": event["correlation_reason"].strip(),
                })
            else:
                incomplete_event_ids.append(event_id)
            safe_events.append(safe_event)

        link_ids: set[str] = set()
        incomplete_link_ids: list[str] = []
        safe_links: list[dict[str, str]] = []
        invalid_link_ids: list[str] = []

        for index, link in enumerate(normalized_links):
            if not isinstance(link, dict):
                raise ValueError(f"links[{index}] must be an object")
            extra = set(link) - self.SYNTHETIC_LINK_FIELDS
            if extra:
                raise ValueError(f"links[{index}] contains unsupported fields: {', '.join(sorted(extra))}")
            link_id = self._synthetic_id(link.get("link_id"), f"links[{index}].link_id")
            if link_id in link_ids:
                raise ValueError(f"duplicate link_id: {link_id}")
            link_ids.add(link_id)
            source_id = self._synthetic_id(link.get("from_transaction_id"), f"links[{index}].from_transaction_id")
            target_id = self._synthetic_id(link.get("to_transaction_id"), f"links[{index}].to_transaction_id")
            if source_id == target_id:
                raise ValueError(f"link {link_id} cannot connect a transaction to itself")
            if source_id not in transaction_ids or target_id not in transaction_ids:
                if not allow_incomplete:
                    raise ValueError(f"link {link_id} references an unknown transaction")
                invalid_link_ids.append(link_id)
                continue
            relation = link.get("relation_type")
            if not isinstance(relation, str) or relation.strip() not in self.ALLOWED_RELATION_TYPES:
                raise ValueError(f"link {link_id} has an unsupported relation_type")
            missing = [
                field for field in ("source", "occurred_at", "correlation_reason")
                if not isinstance(link.get(field), str) or not link[field].strip()
            ]
            if link.get("data_mode") != "synthetic":
                missing.append("data_mode=synthetic")
            if missing and not allow_incomplete:
                raise ValueError(f"link {link_id} is incomplete: {missing[0]}")
            if missing:
                incomplete_link_ids.append(link_id)
                continue
            safe_links.append({
                "link_id": link_id,
                "from_transaction_id": source_id,
                "to_transaction_id": target_id,
                "relation_type": relation.strip(),
                "source": link["source"].strip(),
                "occurred_at": self._synthetic_time(link["occurred_at"], f"links[{index}].occurred_at"),
                "correlation_reason": link["correlation_reason"].strip(),
                "data_mode": "synthetic",
            })

        adjacency = {transaction_id: set() for transaction_id in transaction_ids}
        for link in safe_links:
            left = link["from_transaction_id"]
            right = link["to_transaction_id"]
            adjacency[left].add(right)
            adjacency[right].add(left)

        components: list[list[str]] = []
        unseen = set(transaction_ids)
        while unseen:
            root = min(unseen)
            stack = [root]
            component: set[str] = set()
            while stack:
                current = stack.pop()
                if current in component:
                    continue
                component.add(current)
                unseen.discard(current)
                stack.extend(sorted(adjacency[current] - component, reverse=True))
            components.append(sorted(component))
        components.sort(key=lambda item: item[0])

        metadata_complete = not incomplete_event_ids and not incomplete_link_ids and not invalid_link_ids
        connected = len(components) == 1
        multi_transaction = len(transaction_ids) > 1
        chain_complete = metadata_complete and connected and multi_transaction
        if chain_complete:
            status = "COMPLETE"
        elif not multi_transaction:
            status = "SINGLE_TRANSACTION"
        elif not connected:
            status = "DISCONNECTED"
        else:
            status = "INCOMPLETE"

        return {
            "status": status,
            "chain_complete": chain_complete,
            "connected": connected,
            "transaction_ids": sorted(transaction_ids),
            "components": components,
            "events": sorted(safe_events, key=lambda item: item["event_id"]),
            "links": sorted(safe_links, key=lambda item: item["link_id"]),
            "incomplete_event_ids": sorted(incomplete_event_ids),
            "incomplete_link_ids": sorted(incomplete_link_ids),
            "invalid_link_ids": sorted(invalid_link_ids),
            "proof_scope": "synthetic_transaction_connectivity_only_not_fraud_or_guilt",
            "final_proof": False,
        }
