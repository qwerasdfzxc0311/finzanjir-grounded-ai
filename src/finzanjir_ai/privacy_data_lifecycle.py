from datetime import datetime, timedelta, timezone
from typing import Any


class PrivacyDataLifecycle:
    """Enforce minimal policy, role, retention, and disposal boundaries."""

    def describe_policy(
        self,
        *,
        data_type: str,
        purpose: str,
        retention_days: int,
        allowed_roles: list[str],
        disposal: str,
    ) -> dict[str, Any]:
        if retention_days < 0:
            raise ValueError("retention_days must be non-negative")
        return {
            "data_type": data_type,
            "purpose": purpose,
            "retention_days": retention_days,
            "allowed_roles": list(allowed_roles),
            "disposal": disposal,
        }

    def filter_for_role(
        self,
        record: dict[str, Any],
        *,
        role: str,
        allowed_roles: list[str],
    ) -> dict[str, Any]:
        if role in allowed_roles:
            return dict(record)

        # Citizen-facing views expose only non-sensitive case state.
        return {
            key: record[key]
            for key in ("case_id", "status")
            if key in record
        }

    def apply_retention(
        self,
        *,
        record: dict[str, Any],
        created_at: datetime,
        retention_days: int,
        now: datetime | None = None,
        disposal: str = "archive_then_delete",
    ) -> dict[str, Any]:
        if retention_days < 0:
            raise ValueError("retention_days must be non-negative")

        current = now or datetime.now(timezone.utc)
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)

        expires_at = created_at + timedelta(days=retention_days)
        expired = current >= expires_at
        return {
            "expired": expired,
            "disposition": disposal if expired else "retain",
            "record": {} if expired else dict(record),
        }

    def resolve_policy(self, *, policy: dict[str, Any] | None, action: str) -> dict[str, Any]:
        if policy is None:
            return {
                "allowed": False,
                "decision": "policy_missing",
                "reason": f"Cannot {action}: no approved data policy is available.",
            }
        return {"allowed": True, "decision": "policy_present", "reason": "Approved policy is available."}
