import json
from pathlib import Path


def test_sixteen_layer_window_contract_matches_canonical_ids():
    contract = json.loads(Path("contracts/layers_v1.json").read_text(encoding="utf-8"))

    assert contract["version"] == "1.0"
    assert len(contract["layers"]) == 16
    assert [layer["id"] for layer in contract["layers"]] == [
        f"layer_{index:02d}" for index in range(1, 17)
    ]

    allowed_states = {"current", "prototype", "proposal", "future"}
    for layer in contract["layers"]:
        assert layer["state"] in allowed_states
        assert layer["implementation_status"] in {"planned", "implemented"}
        assert layer["label"]
        assert layer["simple_explanation"]
        assert layer["technical_role"]


def test_layer_crosswalk_contains_all_sixteen_layers():
    contract = json.loads(Path("contracts/layers_v1.json").read_text(encoding="utf-8"))
    assert set(contract["canonical_crosswalk"]) == {
        f"layer_{index:02d}" for index in range(1, 17)
    }
