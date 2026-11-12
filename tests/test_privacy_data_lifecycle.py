from datetime import datetime, timezone, timedelta

from finzanjir_ai.privacy_data_lifecycle import PrivacyDataLifecycle


def test_policy_declares_data_type_purpose_retention_access_and_disposal():
    lifecycle = PrivacyDataLifecycle()
    policy = lifecycle.describe_policy(
        data_type="case_record",
        purpose="case_review",
        retention_days=30,
        allowed_roles=["reviewer"],
        disposal="archive_then_delete",
    )

    assert policy == {
        "data_type": "case_record",
        "purpose": "case_review",
        "retention_days": 30,
        "allowed_roles": ["reviewer"],
        "disposal": "archive_then_delete",
    }


def test_unauthorized_role_cannot_read_protected_data():
    lifecycle = PrivacyDataLifecycle()
    record = {
        "case_id": "CASE-1",
        "status": "OPEN",
        "account_number": "1234567890",
        "internal_rule_id": "RULE-SECRET",
    }

    visible = lifecycle.filter_for_role(record, role="citizen", allowed_roles=["reviewer"])

    assert visible == {"case_id": "CASE-1", "status": "OPEN"}
    assert "account_number" not in visible
    assert "internal_rule_id" not in visible


def test_retention_expiry_marks_record_for_disposal_and_hides_payload():
    lifecycle = PrivacyDataLifecycle()
    created_at = datetime.now(timezone.utc) - timedelta(days=31)

    result = lifecycle.apply_retention(
        record={"case_id": "CASE-2", "status": "OPEN", "secret": "x"},
        created_at=created_at,
        retention_days=30,
    )

    assert result["expired"] is True
    assert result["disposition"] == "archive_then_delete"
    assert result["record"] == {}


def test_active_retention_preserves_record():
    lifecycle = PrivacyDataLifecycle()
    created_at = datetime.now(timezone.utc) - timedelta(days=5)

    result = lifecycle.apply_retention(
        record={"case_id": "CASE-3", "status": "OPEN"},
        created_at=created_at,
        retention_days=30,
    )

    assert result["expired"] is False
    assert result["record"] == {"case_id": "CASE-3", "status": "OPEN"}


def test_missing_policy_records_explicit_decision_instead_of_silent_data_action():
    lifecycle = PrivacyDataLifecycle()

    result = lifecycle.resolve_policy(policy=None, action="export")

    assert result["allowed"] is False
    assert result["decision"] == "policy_missing"
    assert result["reason"]


def test_unapproved_or_non_allowlisted_policy_fails_closed():
    lifecycle = PrivacyDataLifecycle()

    assert lifecycle.resolve_policy(
        policy={"approved": False, "allowed_actions": ["export"]},
        action="export",
    )["allowed"] is False
    assert lifecycle.resolve_policy(
        policy={"approved": True, "allowed_actions": ["read"]},
        action="export",
    )["decision"] == "action_not_authorized"
    assert lifecycle.resolve_policy(
        policy={"approved": "true", "allowed_actions": ["export"]},
        action="export",
    )["decision"] == "policy_not_approved"


def test_unknown_roles_receive_no_record_fields():
    lifecycle = PrivacyDataLifecycle()
    record = {"case_id": "CASE-9", "status": "OPEN", "secret": "x"}

    assert lifecycle.filter_for_role(record, role="citizen", allowed_roles=["reviewer"]) == {
        "case_id": "CASE-9", "status": "OPEN"
    }
    assert lifecycle.filter_for_role(record, role="unknown-role", allowed_roles=["reviewer"]) == {}


def test_policy_rejects_boolean_retention_and_invalid_role_or_disposal():
    import pytest

    with pytest.raises(ValueError, match="retention_days"):
        PrivacyDataLifecycle().describe_policy(
            data_type="case", purpose="review", retention_days=True,
            allowed_roles=["reviewer"], disposal="delete",
        )
    with pytest.raises(ValueError, match="allowed_roles"):
        PrivacyDataLifecycle().describe_policy(
            data_type="case", purpose="review", retention_days=30,
            allowed_roles=["reviewer", ""], disposal="delete",
        )
    with pytest.raises(ValueError, match="disposal"):
        PrivacyDataLifecycle().describe_policy(
            data_type="case", purpose="review", retention_days=30,
            allowed_roles=["reviewer"], disposal="keep_forever",
        )


def test_retention_rejects_invalid_timestamp_and_disposal_method():
    import pytest

    with pytest.raises(ValueError, match="created_at"):
        PrivacyDataLifecycle().apply_retention(
            record={"case_id": "CASE-X"}, created_at="yesterday", retention_days=30
        )
    with pytest.raises(ValueError, match="disposal"):
        PrivacyDataLifecycle().apply_retention(
            record={"case_id": "CASE-X"}, created_at=datetime.now(timezone.utc),
            retention_days=30, disposal="unknown",
        )
