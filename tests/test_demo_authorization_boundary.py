import pytest

from finzanjir_ai.prototype.flow import build_system_flow


def test_system_flow_rejects_non_boolean_cross_bank_authorization():
    flow = build_system_flow()
    transaction = {
        "transaction_id": "TX-AUTH-TYPE-001",
        "bank_id": "bank-a",
        "amount": 2500,
        "occurred_at": "2026-11-11T00:00:00Z",
        "synthetic": True,
        "device_id": "device-1",
        "network_id": "network-1",
        "cross_bank_authorized": 1,
    }

    with pytest.raises(ValueError, match="boolean"):
        flow.execute(transaction, knowledge_index=flow.demo_knowledge_index())


def test_demo_decision_is_explicitly_marked_as_synthetic_demo():
    flow = build_system_flow()
    transaction = {
        "transaction_id": "TX-DEMO-BOUNDARY-001",
        "bank_id": "bank-a",
        "amount": 2500,
        "occurred_at": "2026-11-11T00:00:00Z",
        "synthetic": True,
        "device_id": "device-1",
        "network_id": "network-1",
        "cross_bank_authorized": True,
    }

    result = flow.execute(transaction, knowledge_index=flow.demo_knowledge_index())

    assert result["decision"]["decision"]["decision_origin"] == "synthetic_demo"
    assert result["decision"]["decision"]["actor_type"] == "synthetic_demo"
    assert result["decision"]["decision"]["is_authoritative"] is False
