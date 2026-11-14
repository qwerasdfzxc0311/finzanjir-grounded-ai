import json
from pathlib import Path


BENCHMARK_PATH = Path(__file__).parent.parent / "benchmarks" / "keyless_language_understanding_v1.json"


def test_keyless_language_benchmark_has_unique_cases_and_required_language_coverage():
    benchmark = json.loads(BENCHMARK_PATH.read_text(encoding="utf-8"))
    cases = benchmark["cases"]

    assert benchmark["benchmark_id"] == "FINZANJIR-KEYLESS-LANG-UNDERSTANDING-v1"
    assert len(cases) >= 50
    assert len({case["id"] for case in cases}) == len(cases)
    assert {"uz-Latn", "uz-Cyrl", "kaa", "kk", "ru", "en"} <= {
        case["language"] for case in cases
    }
    assert {"normalization", "intent", "concept_retrieval", "context_followup", "out_of_corpus", "safety"} <= {
        case["layer"] for case in cases
    }
    assert all(case["query"].strip() for case in cases)
    assert all(case["expected_intent"].strip() for case in cases)


def test_benchmark_keeps_current_information_and_missing_evidence_separate_from_project_rag():
    benchmark = json.loads(BENCHMARK_PATH.read_text(encoding="utf-8"))
    intents = {case["expected_intent"] for case in benchmark["cases"]}

    assert "external_current_info" in intents
    assert "safety" in intents
    assert "project" in intents
    assert "project_overview" in intents
