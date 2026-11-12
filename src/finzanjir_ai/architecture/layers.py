from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
import json
from pathlib import Path
from typing import Any


_ALLOWED_STATUSES = frozenset({"PLANNED", "PARTIAL", "COMPLETE"})


@lru_cache(maxsize=1)
def _load_contract() -> tuple[dict[str, Any], ...]:
    contract_path = Path(__file__).resolve().parents[3] / "contracts" / "layers_v2.json"
    if not contract_path.is_file():
        raise RuntimeError("canonical 16-layer implementation contract is missing")
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if contract.get("schema_version") != "2.0":
        raise RuntimeError("unsupported 16-layer contract version")
    layers = contract.get("layers")
    if not isinstance(layers, list) or len(layers) != 16:
        raise RuntimeError("16-layer contract must contain exactly 16 layers")

    ids: set[str] = set()
    for layer in layers:
        if not isinstance(layer, dict):
            raise RuntimeError("layer entry must be an object")
        layer_id = layer.get("id")
        if not isinstance(layer_id, str) or not layer_id or layer_id in ids:
            raise RuntimeError("layer IDs must be unique non-empty strings")
        ids.add(layer_id)
        if layer.get("status") not in _ALLOWED_STATUSES:
            raise RuntimeError(f"invalid implementation status for {layer_id}")
        for field in ("label", "evidence_refs", "acceptance_criteria", "remaining_work"):
            if field not in layer:
                raise RuntimeError(f"layer {layer_id} missing {field}")
        if not isinstance(layer["evidence_refs"], list) or not isinstance(layer["acceptance_criteria"], list) or not isinstance(layer["remaining_work"], list):
            raise RuntimeError(f"layer {layer_id} lists are malformed")
    return tuple(deepcopy(layers))


def get_layer_registry() -> tuple[dict[str, Any], ...]:
    return tuple(deepcopy(layer) for layer in _load_contract())


def get_layer_status_summary() -> dict[str, int]:
    layers = _load_contract()
    return {
        "total": len(layers),
        "complete": sum(layer["status"] == "COMPLETE" for layer in layers),
        "partial": sum(layer["status"] == "PARTIAL" for layer in layers),
        "planned": sum(layer["status"] == "PLANNED" for layer in layers),
    }


def build_layer_trace(transaction_id: str) -> tuple[dict[str, Any], ...]:
    return tuple(
        {
            "layer_id": layer["id"],
            "label": layer["label"],
            "transaction_id": transaction_id,
            "status": layer["status"],
            "evidence_refs": list(layer["evidence_refs"]),
            "acceptance_criteria": list(layer["acceptance_criteria"]),
            "remaining_work": list(layer["remaining_work"]),
        }
        for layer in _load_contract()
    )
