"""Contract tests for the ZIP-to-code 16-layer requirements crosswalk."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = ROOT / "contracts" / "requirements_traceability_v1.json"


def test_traceability_matrix_covers_all_sixteen_zip_requirements():
    matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    layers = matrix["layers"]
    assert matrix["requirement_count"] == 16
    assert len(layers) == 16
    assert [item["requirement_id"] for item in layers] == [f"REQ-{i:03d}" for i in range(1, 17)]
    assert [item["layer_id"] for item in layers] == [f"L{i:02d}" for i in range(1, 17)]


def test_every_layer_has_code_test_and_remaining_gap_references():
    matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    for layer in matrix["layers"]:
        assert layer["status"] == "PARTIAL"
        assert layer["evidence_scope"] == "synthetic_prototype_only"
        assert layer["code_refs"], layer["requirement_id"]
        assert layer["test_refs"], layer["requirement_id"]
        assert layer["remaining_gaps"], layer["requirement_id"]
        for reference in layer["code_refs"] + layer["test_refs"]:
            if reference.endswith("/"):
                target = ROOT / reference.rstrip("/")
                assert target.is_dir(), (layer["requirement_id"], reference)
            elif reference == "tests/" or reference == "src/finzanjir_ai/knowledge":
                assert (ROOT / reference).is_dir(), (layer["requirement_id"], reference)
            elif reference.startswith("GitHub Actions"):
                continue
            else:
                assert (ROOT / reference).exists(), (layer["requirement_id"], reference)


def test_cross_bank_and_production_claims_remain_explicitly_blocked():
    matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    assert "Cross-Bank almashinuvi qonuniy va xavfsizlik ruxsatisiz o‘chiq qoladi." in matrix["safety_invariants"]
    assert all(layer["status"] != "COMPLETE" for layer in matrix["layers"])
    assert all(layer["evidence_scope"] == "synthetic_prototype_only" for layer in matrix["layers"])
