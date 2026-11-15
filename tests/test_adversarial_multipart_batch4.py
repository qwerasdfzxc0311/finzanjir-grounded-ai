import json
from pathlib import Path


PATH = Path(__file__).parents[1] / "benchmarks" / "adversarial_multipart_batch4_v1.json"


def load_batch():
    return json.loads(PATH.read_text(encoding="utf-8"))


def test_batch_four_has_60_balanced_prompts():
    batch = load_batch()
    assert batch["batch_count"] == 60
    assert batch["language_distribution"] == {
        "uz-Latn": 10, "uz-Cyrl": 10, "ru": 10,
        "en": 10, "kk": 10, "kaa": 10,
    }
    assert len(batch["cases"]) == 60


def test_batch_four_uses_grounded_generation_not_prewritten_answers():
    batch = load_batch()
    assert all(c["expected_answer_mode"] == "grounded_generative" for c in batch["cases"])
    assert all(c["expected_evidence_ids"] == [] for c in batch["cases"])
    assert all(c["evidence_mapping_status"] == "pending_source_level_human_review" for c in batch["cases"])


def test_batch_four_covers_key_adversarial_families():
    families = {c["family"] for c in load_batch()["cases"]}
    assert {
        "multi_part", "status_trap", "legal_trap", "false_positive",
        "follow_up", "privacy", "comparison", "implementation",
        "recovery", "near_miss",
    } <= families


def test_adversarial_prompts_have_explicit_safe_evaluation_notes():
    cases = load_batch()["cases"]
    for family in ("near_miss", "legal_trap", "status_trap", "false_positive", "recovery"):
        assert all(c["evaluation_note"].strip() for c in cases if c["family"] == family)
