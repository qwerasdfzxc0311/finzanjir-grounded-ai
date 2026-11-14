import json
from pathlib import Path

from finzanjir_ai.orchestration.task_intent import classify_task_type


FIXTURE = Path(__file__).parent.parent / "benchmarks" / "question_decomposition_diagnostic_v1.json"


def test_question_decomposition_fixture_has_safe_and_complete_case_contracts():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    cases = data["cases"]
    assert data["benchmark_id"] == "FINZANJIR-QUESTION-DECOMPOSITION-v1"
    assert data["corpus_version"] == "0.6"
    assert len(cases) >= 12
    assert len({case["id"] for case in cases}) == len(cases)
    assert {"uz-Latn", "uz-Cyrl", "ru", "en", "kk", "kaa"} <= {
        case["language"] for case in cases
    }
    for case in cases:
        assert case["query"].strip()
        assert case["expected_domain_route"] == "project"
        assert case["expected_task_type"].strip()
        assert len(case["subquestions"]) >= 2
        assert all(item["question"].strip() for item in case["subquestions"])
        assert all(item["knowledge_status"] for item in case["subquestions"])
        assert all(isinstance(item["evidence_ids"], list) for item in case["subquestions"])
        assert case["answer_policy"]["answer_supported_parts"] is True
        assert case["answer_policy"]["withhold_unsupported_parts"] is True


def test_external_comparison_cases_do_not_assume_external_knowledge():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    comparison_cases = [
        case for case in data["cases"]
        if case["expected_task_type"] in {"comparison"}
    ]
    assert comparison_cases
    for case in comparison_cases:
        external_parts = [
            item for item in case["subquestions"]
            if item["knowledge_status"] == "unknown_external"
        ]
        assert external_parts
        assert case["answer_policy"]["withhold_unsupported_parts"] is True


def test_fixture_never_treats_comparison_prompts_as_canonical_facts():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert data["safety"]["canonical_corpus_mutable"] is False
    assert data["safety"]["external_sources_auto_ingested"] is False
    assert data["safety"]["real_customer_or_bank_data"] is False


def test_runtime_task_type_is_not_misrepresented_as_existing_classifier():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert all("expected_task_type" in case for case in data["cases"])
    assert all("expected_domain_route" in case for case in data["cases"])



def test_multilingual_task_intent_baseline_matches_fixture():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    for case in data["cases"]:
        assert classify_task_type(case["query"]) == case["expected_task_type"], case["id"]


def test_task_intent_baseline_handles_paraphrases_and_common_typos():
    examples = {
        "Nimasi bilan o‘xshash tizimlardan ajralib turadi?": "comparison",
        "Чем эта система отличается от других?": "comparison",
        "How does the platform work after a risk signal?": "process",
        "FINZANJIRning arxitekturasi va qatlamlari qanday?": "architecture",
        "Qaysi imkoniyatlar hozir prototipda bor, qaysilari reja?": "status_audit",
        "Неге бұл жоба керек?": "reason",
    }
    for query, expected in examples.items():
        assert classify_task_type(query) == expected, query



def test_expected_evidence_ids_are_curated_only_for_internal_knowledge_parts():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    known_ids = {
        "ck_003252", "ck_003254", "ck_003256", "ck_003257",
        "ck_003258", "ck_003264", "ck_003274", "ck_003275",
    }
    for case in data["cases"]:
        for subquestion in case["subquestions"]:
            expected = set(subquestion["evidence_ids"])
            assert expected <= known_ids
            if subquestion["knowledge_status"] in {
                "unknown_external",
                "unknown_until_production_evidence",
                "unknown_until_implementation_evidence",
                "unknown_until_evidence_review",
            }:
                assert not expected


def test_prototype_implementation_status_requires_code_or_test_evidence():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    status_case = next(case for case in data["cases"] if case["id"] == "STA-UZ-001")
    implementation_part = next(
        item for item in status_case["subquestions"] if item["id"] == "a"
    )
    assert implementation_part["knowledge_status"] == "unknown_until_implementation_evidence"
    assert implementation_part["required_action"] == "inspect_current_code_and_test_artifacts"
