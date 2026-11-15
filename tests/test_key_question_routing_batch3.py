import json
from pathlib import Path


PATH = Path(__file__).parents[1] / "benchmarks" / "key_question_routing_batch3_v1.json"


def load_batch():
    return json.loads(PATH.read_text(encoding="utf-8"))


def test_key_question_batch_has_60_prompts_balanced_across_six_languages():
    batch = load_batch()
    assert batch["batch_count"] == 60
    assert batch["language_distribution"] == {
        "uz-Latn": 10, "uz-Cyrl": 10, "ru": 10,
        "en": 10, "kk": 10, "kaa": 10,
    }
    assert len(batch["cases"]) == 60


def test_only_existing_vetted_intents_are_marked_canonical():
    batch = load_batch()
    canonical = [c for c in batch["cases"] if c["expected_answer_mode"] == "canonical_deterministic"]
    assert len(canonical) == 36
    assert {c["family"] for c in canonical} == {
        "project_overview", "author_motivation", "bank_authority",
        "signal_guilt", "case_definition", "fraud_graph",
    }
    assert all(c["canonical_answer_status"] == "existing_runtime_handler_to_verify" for c in canonical)


def test_other_important_questions_stay_grounded_and_not_scripted():
    batch = load_batch()
    grounded = [c for c in batch["cases"] if c["expected_answer_mode"] == "grounded_generative"]
    assert len(grounded) == 24
    assert {c["family"] for c in grounded} == {"c_model", "layers", "risk_score", "cross_match"}
    assert all(c["canonical_answer_status"] == "not_canonical_requires_grounded_generation" for c in grounded)


def test_evidence_and_language_review_are_not_falsely_marked_complete():
    batch = load_batch()
    for case in batch["cases"]:
        assert case["expected_evidence_ids"] == []
        assert case["evidence_mapping_status"] == "pending_source_level_human_review"
        assert case["query"].strip()


def test_critical_canonical_questions_keep_fraud_safety_boundaries():
    batch = load_batch()
    safety = " ".join(batch["safety_rules"]).lower()
    assert "not proof of guilt" in safety
    assert "no autonomous bank-card blocking" in safety
    assert "keyword-only triggering" in safety
