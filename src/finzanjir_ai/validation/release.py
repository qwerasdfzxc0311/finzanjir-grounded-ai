from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def _read_json(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def validate_release() -> dict:
    failures: list[str] = []

    canonical = _read_json("data/canonical_knowledge_v0.6.json")
    architecture = _read_json("contracts/architecture_v1.json")
    data_model = _read_json("contracts/data_model_v1.json")
    layers = _read_json("contracts/layers_v1.json")
    event = _read_json("contracts/event_envelope_v1.json")

    records = canonical.get("records", [])
    concepts = {str(record.get("canonical_concept_id")) for record in records}
    if len(records) != 8804:
        failures.append("canonical_records")
    if len(concepts) != 2060:
        failures.append("canonical_concepts")
    if canonical.get("finzanjir_architecture_manifest", {}).get("layer_count") != 16:
        failures.append("canonical_manifest_layers")

    if architecture.get("ai_context_separation", {}).get("ai_can_write_authoritative_knowledge") is not False:
        failures.append("ai_authoritative_write")
    if architecture.get("access_boundaries", {}).get("bank_internal", {}).get("cross_bank_data") is not False:
        failures.append("bank_internal_boundary")

    if len(data_model.get("objects", {})) < 11:
        failures.append("data_model_objects")
    if len(layers.get("layers", [])) != 16:
        failures.append("layer_contract")
    if len(event.get("required", [])) != 8:
        failures.append("event_envelope")

    return {
        "ok": not failures,
        "checks_failed": failures,
        "canonical_records": len(records),
        "canonical_concepts": len(concepts),
        "layers": len(layers.get("layers", [])),
    }
