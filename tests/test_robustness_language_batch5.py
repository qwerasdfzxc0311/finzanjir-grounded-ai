import json
from pathlib import Path


PATH = Path(__file__).parents[1] / "benchmarks" / "robustness_language_batch5_v1.json"


def load_batch():
    return json.loads(PATH.read_text(encoding="utf-8"))


def test_batch_five_has_36_prompts_balanced_across_six_languages():
    batch = load_batch()
    assert batch["batch_count"] == 36
    assert batch["language_distribution"] == {
        "uz-Latn": 6, "uz-Cyrl": 6, "ru": 6,
        "en": 6, "kk": 6, "kaa": 6,
    }
    assert len(batch["cases"]) == 36


def test_batch_five_covers_robustness_and_language_families():
    batch = load_batch()
    assert {
        "history_contamination", "prompt_injection", "contradiction",
        "ambiguity", "language_quality", "author_critique",
    } == set(batch["coverage_families"])


def test_only_ambiguous_cases_request_clarification():
    batch = load_batch()
    for case in batch["cases"]:
        expected = "abstain_or_clarify" if case["family"] == "ambiguity" else "grounded_generative"
        assert case["expected_answer_mode"] == expected


def test_batch_five_has_no_unreviewed_gold_answers_or_evidence():
    batch = load_batch()
    for case in batch["cases"]:
        assert case["expected_evidence_ids"] == []
        assert case["evidence_mapping_status"] == "pending_source_level_human_review"
        assert case["evaluation_note"].strip()
