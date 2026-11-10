import pytest

from finzanjir_ai.cross_bank.matcher import CrossBankMatcher


def test_cross_bank_match_requires_explicit_authorized_scope():
    matcher = CrossBankMatcher()
    records = [
        {"transaction_id": "tx-a", "bank_id": "bank-a", "device_id": "device-1"},
        {"transaction_id": "tx-b", "bank_id": "bank-b", "device_id": "device-1"},
    ]
    with pytest.raises(ValueError, match="authorized"):
        matcher.match(records, scope="cross_bank", authorized_exchange=False)


def test_authorized_cross_bank_match_creates_graph_edge():
    matcher = CrossBankMatcher()
    records = [
        {"transaction_id": "tx-a", "bank_id": "bank-a", "device_id": "device-1"},
        {"transaction_id": "tx-b", "bank_id": "bank-b", "device_id": "device-1"},
    ]
    result = matcher.match(records, scope="cross_bank", authorized_exchange=True)
    assert result.matches[0]["scope"] == "cross_bank"
    assert result.graph_edges[0]["edge_type"] == "SHARED_DEVICE"


def test_cross_bank_match_requires_explicit_scope():
    matcher = CrossBankMatcher()
    records = [
        {"transaction_id": "tx-a", "bank_id": "bank-a", "device_id": "device-1"},
        {"transaction_id": "tx-b", "bank_id": "bank-b", "device_id": "device-1"},
    ]
    with pytest.raises(ValueError, match="scope"):
        matcher.match(records, scope="bank_internal", authorized_exchange=True)
