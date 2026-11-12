import json
from pathlib import Path

from finzanjir_ai.risk.registry import SIGNAL_REGISTRY


ROOT = Path(__file__).resolve().parents[1]
RULES = json.loads((ROOT / "contracts" / "signal_detector_rules_v1.json").read_text(encoding="utf-8"))
GATES = json.loads((ROOT / "contracts" / "signal_source_legal_gates_v1.json").read_text(encoding="utf-8"))


def test_source_legal_gate_matrix_covers_all_40_detector_rules():
    entries = GATES["signals"]
    assert len(entries) == 40
    assert {item["signal_id"] for item in entries} == set(SIGNAL_REGISTRY)
    assert {item["signal_id"] for item in entries} == {item["signal_id"] for item in RULES["detectors"]}


def test_source_legal_gate_fields_match_detector_feature_contract():
    gates = {item["signal_id"]: item for item in GATES["signals"]}
    rules = {item["signal_id"]: item for item in RULES["detectors"]}
    for signal_id, gate in gates.items():
        rule = rules[signal_id]
        assert gate["required_feature_fields"] == rule["required_features"]
        assert gate["optional_feature_fields"] == rule.get("optional_features", [])
        assert gate["status"] == "synthetic_test_only"
        assert gate["source_availability"] == "not_verified_with_any_bank"
        assert gate["lawful_basis_status"] == "not_assessed_unverified_requires_legal_review"
        assert gate["candidate_source_classes"]
        assert gate["cross_bank_data_enabled"] is False


def test_no_signal_is_marked_legally_approved_or_authorized_for_raw_identity_ingestion():
    assert GATES["status"] == "candidate_source_mapping_not_legal_approval"
    assert GATES["cross_bank_data_enabled"] is False
    for gate in GATES["signals"]:
        assert "no_full_card_number" in gate["raw_data_restrictions"]
        assert "no_account_number" in gate["raw_data_restrictions"]
        assert "no_clipboard_content" in gate["raw_data_restrictions"]
        assert gate["automated_action"] == "no_payment_block_or_authoritative_customer_action"
