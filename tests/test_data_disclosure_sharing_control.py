import pytest

from finzanjir_ai.data_sharing.policy import DataDisclosurePolicy


def test_external_share_requires_purpose_permission_recipient_and_minimal_fields():
    policy = DataDisclosurePolicy(
        allowed_recipients={"bank-b"},
        allowed_fields={"transaction_id", "bank_id", "risk_id"},
    )

    with pytest.raises(ValueError, match="permission"):
        policy.prepare_transfer(
            purpose="fraud_review",
            recipient="bank-b",
            requested_fields=["transaction_id", "bank_id"],
            permission=False,
        )

    with pytest.raises(ValueError, match="recipient"):
        policy.prepare_transfer(
            purpose="fraud_review",
            recipient="bank-c",
            requested_fields=["transaction_id"],
            permission=True,
        )

    with pytest.raises(ValueError, match="minimal"):
        policy.prepare_transfer(
            purpose="fraud_review",
            recipient="bank-b",
            requested_fields=["transaction_id", "bank_id", "risk_id", "customer_name"],
            permission=True,
        )


def test_external_share_returns_only_minimal_authorized_fields_and_audit_record():
    policy = DataDisclosurePolicy(
        allowed_recipients={"bank-b"},
        allowed_fields={"transaction_id", "bank_id", "risk_id"},
    )

    result = policy.prepare_transfer(
        purpose="fraud_review",
        recipient="bank-b",
        requested_fields=["transaction_id", "bank_id"],
        permission=True,
    )

    assert result["payload_fields"] == ["transaction_id", "bank_id"]
    assert result["recipient"] == "bank-b"
    assert result["purpose"] == "fraud_review"
    assert result["audit"]["permission"] is True
    assert result["audit"]["requested_fields"] == ["transaction_id", "bank_id"]
