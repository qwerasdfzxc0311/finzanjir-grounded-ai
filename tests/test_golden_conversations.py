import json
from pathlib import Path


FIXTURE = Path(__file__).parent / "fixtures" / "golden_conversations_v1.jsonl"
SUPPORTED_LANGUAGES = {"uz", "kaa", "kk", "ru", "en"}


def test_golden_conversations_cover_all_supported_languages():
    rows = [json.loads(line) for line in FIXTURE.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert {row["language"] for row in rows} == SUPPORTED_LANGUAGES
    assert len({row["id"] for row in rows}) == len(rows)
    for row in rows:
        assert row["messages"]
        assert row["expected_intent"]
        assert row["must_do"]
        assert row["must_not"]
        assert all(message["role"] in {"user", "assistant", "tool", "system"} for message in row["messages"])


def test_plugin_permission_case_requires_host_truth_and_safe_continuation():
    rows = [json.loads(line) for line in FIXTURE.read_text(encoding="utf-8").splitlines() if line.strip()]
    case = next(row for row in rows if row["id"] == "uz-005")
    assert "inspect_trusted_host_capability_snapshot" in case["must_do"]
    assert "continue_preapproved_read_only_actions" in case["must_do"]
    assert "self_grant_permissions" in case["must_not"]
