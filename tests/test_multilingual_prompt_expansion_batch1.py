import json
from pathlib import Path


PATH = Path(__file__).parents[1] / "benchmarks" / "multilingual_prompt_expansion_batch1_v1.json"


def load_batch():
    return json.loads(PATH.read_text(encoding="utf-8"))


def test_multilingual_batch_has_expected_size_and_language_balance():
    batch = load_batch()
    assert batch["batch_count"] == 60
    assert batch["language_distribution"] == {
        "uz-Latn": 10, "uz-Cyrl": 10, "ru": 10,
        "en": 10, "kk": 10, "kaa": 10,
    }
    assert len(batch["cases"]) == 60


def test_prompt_ids_and_queries_are_unique():
    cases = load_batch()["cases"]
    ids = [case["id"] for case in cases]
    queries = [(case["language"], case["query"].casefold()) for case in cases]
    assert len(ids) == len(set(ids))
    assert len(queries) == len(set(queries))


def test_prompts_are_not_pre_scripted_answers_or_canonical_knowledge():
    batch = load_batch()
    assert batch["canonical_corpus_mutable"] is False
    assert batch["data_policy"]["synthetic_queries_only"] is True
    assert batch["data_policy"]["contains_real_customer_or_bank_data"] is False
    for case in batch["cases"]:
        assert case["query"].strip()
        assert case["expected_evidence_ids"] == []
        assert case["evidence_mapping_status"] == "pending_source_level_human_review"
        assert case["expected_answer_mode"] in {
            "grounded_generative", "separate_general_knowledge",
            "canonical_deterministic", "abstain_or_clarify",
        }


def test_general_knowledge_stays_outside_project_domain():
    batch = load_batch()
    general = [case for case in batch["cases"] if case["family"] == "general"]
    assert len(general) == 6
    assert all(case["expected_domain_route"] == "general" for case in general)
    assert all(case["expected_answer_mode"] == "separate_general_knowledge" for case in general)


def test_author_criticism_is_a_near_miss_not_a_canonical_author_answer():
    batch = load_batch()
    traps = [case for case in batch["cases"] if case["author_name_near_miss"]]
    assert len(traps) == 6
    assert all(case["expected_answer_mode"] == "grounded_generative" for case in traps)
