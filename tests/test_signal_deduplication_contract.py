import json
from pathlib import Path

from finzanjir_ai.risk.registry import SIGNAL_REGISTRY


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = json.loads((ROOT / "contracts" / "signal_deduplication_v1.json").read_text(encoding="utf-8"))


def test_deduplication_crosswalk_covers_15_legacy_10_small_and_20_new_candidates():
    legacy = CONTRACT["legacy_signals"]
    small = CONTRACT["small_signals"]
    new = CONTRACT["new_candidates"]

    assert len(legacy) == 15
    assert {item["signal_id"] for item in legacy} == {f"SIG-{index:03d}" for index in range(1, 16)}
    assert len(small) == 10
    assert {item["small_id"] for item in small} == {f"SMALL-{index:03d}" for index in range(1, 11)}
    assert len(new) == 20
    assert {item["signal_id"] for item in new} == {f"SIG-{index:03d}" for index in range(16, 36)}


def test_crosswalk_references_only_registered_signal_ids():
    registered = set(SIGNAL_REGISTRY)
    for item in CONTRACT["legacy_signals"]:
        assert set(item["related_new_ids"]).issubset(registered)
    for item in CONTRACT["small_signals"]:
        assert item["mapping"] in registered
    for item in CONTRACT["new_candidates"]:
        assert item["signal_id"] in registered
        assert set(item["related_legacy_ids"]).issubset(registered)


def test_small_aliases_and_context_only_items_do_not_claim_independent_score():
    small = {item["small_id"]: item for item in CONTRACT["small_signals"]}
    assert small["SMALL-002"]["score_policy"] == "no_independent_score"
    assert small["SMALL-003"]["score_policy"] == "no_independent_score"
    assert small["SMALL-005"]["score_policy"] == "no_independent_score"
    assert small["SMALL-009"]["score_policy"] == "no_independent_score"
    assert small["SMALL-006"]["score_policy"] == "zero"
    assert small["SMALL-008"]["score_policy"].startswith("zero")


def test_crosswalk_preserves_excluded_advanced_signal_source_boundary():
    assert "FINZANJIR_Ilgor_Signallar.docx" in CONTRACT["source_scope"]["excluded_source_documents"]
    assert CONTRACT["policies"]["preserve_legacy_ids"] is True
    assert CONTRACT["policies"]["same_source_event_key_scores_once"] is True
