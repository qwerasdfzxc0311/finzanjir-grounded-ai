import pytest

from finzanjir_ai.cross_bank.matcher import CrossBankMatcher


def test_cross_bank_match_requires_explicit_scope():
    matcher = CrossBankMatcher()
    records = [
        {"bank_id": "bank-a", "transaction_id": "tx-a", "network_id": "net-1"},
        {"bank_id": "bank-b", "transaction_id": "tx-b", "network_id": "net-1"},
    ]

    with pytest.raises(ValueError, match="cross_bank"):
        matcher.match(records, scope="bank_internal", authorized_exchange=True)


def test_cross_bank_match_returns_scoped_matches_without_raw_payloads():
    matcher = CrossBankMatcher()
    records = [
        {"bank_id": "bank-a", "transaction_id": "tx-a", "network_id": "net-1", "amount": 9000},
        {"bank_id": "bank-b", "transaction_id": "tx-b", "network_id": "net-1", "amount": 12000},
    ]

    result = matcher.match(records, scope="cross_bank", authorized_exchange=True)

    assert len(result.matches) == 1
    match = result.matches[0]
    assert {match["bank_id_a"], match["bank_id_b"]} == {"bank-a", "bank-b"}
    assert match["shared_key_type"] == "network_id"
    assert "amount" not in match
    assert "raw_value" not in match


def test_fraud_graph_creates_shared_network_edge():
    matcher = CrossBankMatcher()
    records = [
        {"bank_id": "bank-a", "transaction_id": "tx-a", "network_id": "net-1"},
        {"bank_id": "bank-b", "transaction_id": "tx-b", "network_id": "net-1"},
    ]

    result = matcher.match(records, scope="cross_bank", authorized_exchange=True)

    assert len(result.graph_edges) == 1
    assert result.graph_edges[0]["edge_type"] == "SHARED_NETWORK"
