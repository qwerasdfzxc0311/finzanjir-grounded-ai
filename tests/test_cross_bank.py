import pytest

from finzanjir_ai.cross_bank.matcher import CrossBankMatcher


def test_cross_bank_match_requires_explicit_authorized_scope():
    matcher = CrossBankMatcher()
    signals = [
        {"id": "sig-a", "bank_id": "bank-a", "correlation_key": "device-1"},
        {"id": "sig-b", "bank_id": "bank-b", "correlation_key": "device-1"},
    ]

    with pytest.raises(ValueError, match="authorized"):
        matcher.match(signals, authorized=False)


def test_authorized_cross_bank_match_creates_graph_edge():
    matcher = CrossBankMatcher()
    signals = [
        {"id": "sig-a", "bank_id": "bank-a", "correlation_key": "device-1"},
        {"id": "sig-b", "bank_id": "bank-b", "correlation_key": "device-1"},
        {"id": "sig-c", "bank_id": "bank-a", "correlation_key": "device-2"},
    ]

    result = matcher.match(signals, authorized=True)

    assert result.matches == (("sig-a", "sig-b"),)
    assert result.graph_edges == (("bank-a:sig-a", "bank-b:sig-b"),)
    assert result.scope == "cross_bank"


def test_cross_bank_match_requires_explicit_scope():
    matcher = CrossBankMatcher()
    signals = [{"id": "sig-a", "bank_id": "bank-a", "correlation_key": "device-1"}, {"id": "sig-b", "bank_id": "bank-b", "correlation_key": "device-1"}]
    with pytest.raises(ValueError, match="scope"):
        matcher.match(signals, authorized=True, explicit_scope=False)
