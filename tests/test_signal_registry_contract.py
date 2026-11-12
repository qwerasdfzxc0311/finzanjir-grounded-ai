import json
from pathlib import Path

from finzanjir_ai.risk.registry import (
    FAMILY_CAPS,
    REGISTRY_VERSION,
    SIGNAL_REGISTRY,
)


def test_machine_readable_signal_contract_matches_runtime_registry():
    contract_path = Path(__file__).resolve().parents[1] / "contracts" / "signal_registry_v1.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))

    assert contract["registry_version"] == REGISTRY_VERSION
    assert contract["family_caps"] == FAMILY_CAPS
    assert len(contract["small_signal_mappings"]) == 10
    for mapping in contract["small_signal_mappings"]:
        assert set(mapping["canonical_ids"]).issubset(SIGNAL_REGISTRY)

    contract_signals = {item["signal_id"]: item for item in contract["signals"]}
    assert set(contract_signals) == set(SIGNAL_REGISTRY)

    for signal_id, definition in SIGNAL_REGISTRY.items():
        item = contract_signals[signal_id]
        assert item["family"] == definition.family
        assert item["base_weight"] == definition.weight
        assert item["source_status"] == definition.source_status
        assert item["requires_corroboration"] == definition.requires_corroboration
        assert item["score_eligible"] == definition.score_eligible
