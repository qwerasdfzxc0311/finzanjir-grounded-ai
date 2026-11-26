import json
from pathlib import Path

PATH = Path(__file__).parents[1] / "benchmarks" / "expert_question_routing_batch6_v1.json"


def load_batch():
    return json.loads(PATH.read_text(encoding="utf-8"))


def test_expert_batch_has_24_prompts_balanced_across_six_languages():
    batch = load_batch()
    assert batch["batch_count"] == 24
    assert batch["language_distribution"] == {
        "uz-Latn": 4, "uz-Cyrl": 4, "ru": 4,
        "en": 4, "kk": 4, "kaa": 4,
    }
    assert len(batch["cases"]) == 24


def test_legal_and_international_questions_remain_grounded_until_reviewed():
    batch = load_batch()
    assert {c["family"] for c in batch["cases"]} == {
        "legal_operability_and_data_governance",
        "international_analogues_and_local_adaptation",
    }
    assert all(c["expected_answer_mode"] == "grounded_generative" for c in batch["cases"])
    assert all(c["prepared_answer_status"] == "candidate_prepared_core_pending_review_not_runtime" for c in batch["cases"])
    assert all(c["expected_evidence_ids"] == [] for c in batch["cases"])


def test_legal_safety_boundaries_are_explicit():
    rules = " ".join(load_batch()["safety_rules"]).lower()
    assert "not legal authorization" in rules
    assert "does not automatically remove" in rules
    assert "not proof of identical systems" in rules


def test_all_queries_are_nonempty_and_unique_within_batch():
    cases = load_batch()["cases"]
    queries = [c["query"].strip().casefold() for c in cases]
    assert all(queries)
    assert len(queries) == len(set(queries))
