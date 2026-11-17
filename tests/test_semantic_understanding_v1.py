import json
from pathlib import Path

FIXTURE = Path(__file__).parent / "fixtures" / "semantic_understanding_v1.jsonl"
SUPPORTED_LANGUAGES = {"uz", "kaa", "kk", "ru", "en"}
REQUIRED_DIMENSIONS = {
    "general_vs_project",
    "source_separation",
    "partial_evidence",
    "relevance",
    "dialogue_context",
    "offline_fallback",
}


def _rows():
    return [
        json.loads(line)
        for line in FIXTURE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_semantic_suite_covers_all_languages_and_dimensions():
    rows = _rows()
    assert len(rows) >= 25
    assert {row["language"] for row in rows} == SUPPORTED_LANGUAGES
    assert {row["evaluation_dimension"] for row in rows} == REQUIRED_DIMENSIONS
    assert len({row["id"] for row in rows}) == len(rows)


def test_semantic_cases_require_positive_and_negative_behavior():
    for row in _rows():
        assert row["messages"]
        assert row["expected_intent"]
        assert row["must_do"]
        assert row["must_not"]
        assert row["messages"][0]["role"] == "user"
        assert all(message["role"] in {"user", "assistant", "tool", "system"}
                   for message in row["messages"])


def test_provider_outage_cases_do_not_claim_unverified_local_generation():
    cases = [row for row in _rows()
             if row["evaluation_dimension"] == "offline_fallback"]
    assert len(cases) == 5
    assert all(
        any("local" in item or "tested_local" in item for item in row["must_do"])
        for row in cases
    )
    assert all(
        any("claim" in item or "mislabel" in item for item in row["must_not"])
        for row in cases
    )
