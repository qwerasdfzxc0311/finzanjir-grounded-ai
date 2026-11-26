import json
from pathlib import Path


PATH = Path(__file__).parents[1] / "benchmarks" / "multilingual_prompt_expansion_batch2_v1.json"


def load_batch():
    return json.loads(PATH.read_text(encoding="utf-8"))


def test_batch_two_has_60_prompts_balanced_across_six_languages():
    batch = load_batch()
    assert batch["batch_count"] == 60
    assert batch["language_distribution"] == {
        "uz-Latn": 10, "uz-Cyrl": 10, "ru": 10,
        "en": 10, "kk": 10, "kaa": 10,
    }
    assert len(batch["cases"]) == 60


def test_batch_two_ids_and_prompts_are_unique():
    cases = load_batch()["cases"]
    assert len({c["id"] for c in cases}) == len(cases)
    assert len({(c["language"], c["query"].casefold()) for c in cases}) == len(cases)


def test_batch_two_contains_no_unreviewed_gold_evidence_or_answers():
    batch = load_batch()
    assert batch["canonical_corpus_mutable"] is False
    assert batch["data_policy"]["synthetic_queries_only"] is True
    for case in batch["cases"]:
        assert case["expected_evidence_ids"] == []
        assert case["evidence_mapping_status"] == "pending_source_level_human_review"
        assert case["expected_answer_mode"] == "grounded_generative"


def test_batch_two_covers_fraud_legal_complaint_evaluation_and_adversarial_cases():
    families = {case["family"] for case in load_batch()["cases"]}
    assert {
        "fraud_patterns", "legal_uncertainty", "complaints_recovery",
        "evaluation", "adversarial",
    } <= families


def test_adversarial_score_question_rejects_guilt_inference():
    cases = [c for c in load_batch()["cases"] if c["family"] == "adversarial"]
    assert len(cases) == 6
    assert all("not proof of guilt" in c["evaluation_note"].lower() for c in cases)
