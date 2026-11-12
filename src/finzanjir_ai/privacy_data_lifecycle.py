from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any


class PrivacyDataLifecycle:
    """Enforce strict prototype policy, role, retention, and disposal boundaries."""

    ALLOWED_DISPOSAL = frozenset({"archive_then_delete", "delete", "archive"})

    @staticmethod
    def _required_text(value: Any, field: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field} must be a non-empty string")
        return value.strip()

    @staticmethod
    def _retention_days(value: Any) -> int:
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError("retention_days must be a non-negative integer")
        return value

    def describe_policy(
        self,
        *,
        data_type: str,
        purpose: str,
        retention_days: int,
        allowed_roles: list[str],
        disposal: str,
    ) -> dict[str, Any]:
        data_type = self._required_text(data_type, "data_type")
        purpose = self._required_text(purpose, "purpose")
        retention_days = self._retention_days(retention_days)
        if not isinstance(allowed_roles, list) or not allowed_roles or any(
            not isinstance(role, str) or not role.strip() for role in allowed_roles
        ):
            raise ValueError("allowed_roles must be a non-empty list of role names")
        roles = list(dict.fromkeys(role.strip() for role in allowed_roles))
        disposal = self._required_text(disposal, "disposal")
        if disposal not in self.ALLOWED_DISPOSAL:
            raise ValueError("unsupported disposal method")
        return {
            "data_type": data_type,
            "purpose": purpose,
            "retention_days": retention_days,
            "allowed_roles": roles,
            "disposal": disposal,
        }

    def filter_for_role(
        self,
        record: dict[str, Any],
        *,
        role: str,
        allowed_roles: list[str],
    ) -> dict[str, Any]:
        if not isinstance(record, dict):
            raise ValueError("record must be an object")
        role = self._required_text(role, "role")
        if not isinstance(allowed_roles, list) or any(not isinstance(item, str) for item in allowed_roles):
            raise ValueError("allowed_roles must be a list of role names")
        if role in allowed_roles:
            return dict(record)
        if role == "citizen":
            return {key: record[key] for key in ("case_id", "status") if key in record}
        return {}

    def apply_retention(
        self,
        *,
        record: dict[str, Any],
        created_at: datetime,
        retention_days: int,
        now: datetime | None = None,
        disposal: str = "archive_then_delete",
    ) -> dict[str, Any]:
        if not isinstance(record, dict):
            raise ValueError("record must be an object")
        retention_days = self._retention_days(retention_days)
        if not isinstance(created_at, datetime):
            raise ValueError("created_at must be a datetime")
        if now is not None and not isinstance(now, datetime):
            raise ValueError("now must be a datetime or None")
        disposal = self._required_text(disposal, "disposal")
        if disposal not in self.ALLOWED_DISPOSAL:
            raise ValueError("unsupported disposal method")

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
        action = self._required_text(action, "action")
        if policy is None:
            return {
                "allowed": False,
                "decision": "policy_missing",
                "reason": f"Cannot {action}: no approved data policy is available.",
            }
        if not isinstance(policy, dict) or policy.get("approved") is not True:
            return {
                "allowed": False,
                "decision": "policy_not_approved",
                "reason": f"Cannot {action}: the data policy is not explicitly approved.",
            }
        allowed_actions = policy.get("allowed_actions")
        if not isinstance(allowed_actions, list) or any(not isinstance(item, str) for item in allowed_actions):
            return {
                "allowed": False,
                "decision": "policy_actions_invalid",
                "reason": "The approved policy does not declare valid allowed actions.",
            }
        if action not in allowed_actions:
            return {
                "allowed": False,
                "decision": "action_not_authorized",
                "reason": f"The approved policy does not permit {action}.",
            }
        return {"allowed": True, "decision": "policy_approved", "reason": "Approved policy explicitly permits this action."}
