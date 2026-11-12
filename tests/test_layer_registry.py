import json
from pathlib import Path

from finzanjir_ai.architecture.layers import (
    build_layer_trace,
    get_layer_registry,
    get_layer_status_summary,
)


def test_layer_registry_has_16_evidence_based_statuses_and_acceptance_criteria():
    layers = get_layer_registry()
    summary = get_layer_status_summary()

    assert len(layers) == 16
    assert len({layer["id"] for layer in layers}) == 16
    assert summary == {"total": 16, "complete": 0, "partial": 12, "planned": 4}
    assert all(layer["status"] in {"PARTIAL", "PLANNED", "COMPLETE"} for layer in layers)
    assert all(layer["acceptance_criteria"] for layer in layers)
    assert all(layer["remaining_work"] for layer in layers)
    assert all(layer["status"] != "COMPLETE" or layer["evidence_refs"] for layer in layers)


def test_layer_trace_does_not_claim_all_layers_are_covered():
    trace = build_layer_trace("TX-LAYER-001")

    assert len(trace) == 16
    assert all(item["transaction_id"] == "TX-LAYER-001" for item in trace)
    assert all(item["status"] != "covered" for item in trace)
    assert {item["status"] for item in trace} == {"PARTIAL", "PLANNED"}


def test_layer_registry_contract_and_runtime_trace_match():
    root = Path(__file__).resolve().parents[1]
    contract = json.loads((root / "contracts" / "layers_v2.json").read_text(encoding="utf-8"))
    runtime = get_layer_registry()

    assert [layer["id"] for layer in runtime] == [layer["id"] for layer in contract["layers"]]
    assert [layer["status"] for layer in runtime] == [layer["status"] for layer in contract["layers"]]


def test_layer_registry_returns_detached_data():
    layers = get_layer_registry()
    layers[0]["status"] = "COMPLETE"
    layers[0]["evidence_refs"].clear()

    fresh = get_layer_registry()
    assert fresh[0]["status"] == "PARTIAL"
    assert fresh[0]["evidence_refs"]
