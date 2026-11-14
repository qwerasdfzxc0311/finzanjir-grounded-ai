import json
from pathlib import Path


BENCHMARK_PATH = (
    Path(__file__).parents[1]
    / "benchmarks"
    / "complex_question_benchmark_v1.json"
)


def load_benchmark():
    return json.loads(BENCHMARK_PATH.read_text(encoding="utf-8"))


def test_complex_question_benchmark_has_unique_case_and_subquestion_ids():
    benchmark = load_benchmark()
    cases = benchmark["cases"]

    case_ids = [case["id"] for case in cases]
    assert len(case_ids) == len(set(case_ids))

    for case in cases:
        subquestion_ids = [item["id"] for item in case["subquestions"]]
        assert subquestion_ids
        assert len(subquestion_ids) == len(set(subquestion_ids))


def test_benchmark_covers_comparison_architecture_and_partial_answer():
    benchmark = load_benchmark()
    intents = {case["expected_intent"] for case in benchmark["cases"]}

    assert {
        "comparison",
        "architecture",
        "mechanism_and_benefit",
        "capability_status",
        "mixed_internal_external",
    } <= intents


def test_external_unknowns_do_not_suppress_answerable_internal_parts():
    benchmark = load_benchmark()
    mixed_cases = [
        case
        for case in benchmark["cases"]
        if case["expected_intent"] == "mixed_internal_external"
    ]
    assert mixed_cases

    for case in mixed_cases:
        internal_required = [
            item
            for item in case["subquestions"]
            if item["evidence_scope"] == "canonical_project"
            and item["answer_required"]
        ]
        external_unknown = [
            item
            for item in case["subquestions"]
            if item["evidence_scope"] == "external_research"
            and item["knowledge_state"] == "unknown_until_researched"
        ]
        assert internal_required
        assert external_unknown
        assert any(
            "Answer the internal FINZANJIR part" in behavior
            for behavior in case["required_behavior"]
        )


def test_benchmark_preserves_source_boundary_and_synthetic_data_policy():
    benchmark = load_benchmark()

    assert benchmark["corpus_version"] == "canonical_knowledge_v0.6"
    assert benchmark["corpus_mutable"] is False
    assert benchmark["data_policy"]["synthetic_queries_only"] is True
    assert benchmark["data_policy"]["contains_real_customer_or_bank_data"] is False
    assert benchmark["data_policy"]["external_sources_enter_canonical_corpus"] is False
    assert benchmark["evidence_id_mapping"] == "mapped_to_canonical_v0.6_record_ids_pending_runtime_validation"


def test_every_case_declares_language_intent_and_answer_safety_rules():
    benchmark = load_benchmark()

    for case in benchmark["cases"]:
        assert case["query"].strip()
        assert case["language"] in {"uz", "ru", "en", "kk", "kaa"}
        assert case["expected_intent"]
        assert case["subquestions"]
        assert case["required_behavior"]
        assert case["forbidden_behavior"]
        for subquestion in case["subquestions"]:
            assert subquestion["target"].strip()
            assert subquestion["evidence_scope"] in {
                "canonical_project",
                "external_research",
            }
            assert subquestion["knowledge_state"]
            assert isinstance(subquestion["answer_required"], bool)
            assert "expected_evidence_ids" in subquestion
            assert all(item.startswith(("ck_", "src", "htmlk_")) for item in subquestion["expected_evidence_ids"])
            if subquestion["evidence_scope"] == "external_research" and subquestion["knowledge_state"] == "unknown_until_researched":
                assert subquestion["expected_evidence_ids"] == []
                assert subquestion["evidence_gap_reason"]
