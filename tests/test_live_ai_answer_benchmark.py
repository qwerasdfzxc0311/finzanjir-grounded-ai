import csv
import json
from pathlib import Path

from scripts.run_live_ai_answer_benchmark import run_benchmark, summarize_results


BENCHMARK = Path(__file__).resolve().parents[1] / "benchmarks" / "live_ai_answer_qa_v1.json"


def test_live_answer_benchmark_has_50_unique_synthetic_questions():
    data = json.loads(BENCHMARK.read_text(encoding="utf-8"))
    questions = data["questions"]

    assert data["benchmark_id"] == "finzanjir_live_ai_answer_qa_v1"
    assert len(questions) == 50
    assert len({item["id"] for item in questions}) == 50
    assert all(item["question"].strip() for item in questions)
    assert {item["language"] for item in questions} == {
        "uz", "ru", "en", "kk", "kaa"
    }
    assert data["data_policy"]["contains_real_customer_or_bank_data"] is False


def test_benchmark_summary_counts_transport_abstention_and_provider_failures():
    results = [
        {
            "http_status": 200,
            "json_returned": True,
            "answer_nonempty": True,
            "abstained": False,
            "generation_mode": "extractive_grounded_fallback",
            "provider_status": "provider_failed",
            "provider_diagnostics": [{"provider": "gemini", "status": "rate_limited"}],
        },
        {
            "http_status": 200,
            "json_returned": True,
            "answer_nonempty": True,
            "abstained": True,
            "generation_mode": "language_safe_abstention",
            "provider_status": "provider_failed",
            "provider_diagnostics": [
                {"provider": "gemini", "status": "rate_limited"},
                {"provider": "openrouter", "status": "request_rejected"},
            ],
        },
        {
            "http_status": 503,
            "json_returned": False,
            "answer_nonempty": False,
            "abstained": None,
            "generation_mode": None,
            "provider_status": None,
            "provider_diagnostics": [],
        },
    ]

    summary = summarize_results(results)

    assert summary["total"] == 3
    assert summary["http_2xx"] == 2
    assert summary["json_responses"] == 2
    assert summary["nonempty_answers"] == 2
    assert summary["abstentions"] == 1
    assert summary["provider_failure_categories"] == {
        "gemini:rate_limited": 2,
        "openrouter:request_rejected": 1,
    }


def test_live_benchmark_writes_json_and_csv_without_extra_api_fields(tmp_path, monkeypatch):
    import scripts.run_live_ai_answer_benchmark as benchmark_module

    fixture = {
        "benchmark_id": "synthetic-test",
        "version": 1,
        "corpus_version": "test",
        "questions": [
            {
                "id": "01",
                "language": "uz",
                "topic": "test",
                "question": "FINZANJIR nima?",
                "review_focus": "overview",
            },
            {
                "id": "02",
                "language": "ru",
                "topic": "test",
                "question": "Что такое FINZANJIR?",
                "review_focus": "overview",
            },
        ],
    }
    benchmark_path = tmp_path / "benchmark.json"
    benchmark_path.write_text(json.dumps(fixture), encoding="utf-8")

    class FakeResponse:
        status_code = 200

        @staticmethod
        def json():
            return {
                "answer": "Synthetic grounded answer",
                "abstained": False,
                "generation_mode": "extractive_grounded_fallback",
                "provider_status": "not_attempted",
                "provider_diagnostics": [],
                "knowledge_refs": ["project_0001"],
                "provenance": ["synthetic-fixture"],
            }

    class FakeClient:
        def __init__(self, **_kwargs):
            self.calls = []

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def post(self, url, json):
            self.calls.append((url, json))
            return FakeResponse()

    monkeypatch.setattr(benchmark_module.httpx, "Client", FakeClient)

    result = run_benchmark(
        base_url="https://example.invalid",
        benchmark_path=benchmark_path,
        output_dir=tmp_path / "out",
        delay_ms=0,
    )

    json_path = Path(result["json_path"])
    csv_path = Path(result["csv_path"])
    report = json.loads(json_path.read_text(encoding="utf-8"))

    assert report["summary"]["total"] == 2
    assert report["summary"]["nonempty_answers"] == 2
    assert len(report["results"]) == 2
    assert report["results"][0]["knowledge_refs"] == ["project_0001"]
    assert report["results"][0]["review_focus"] == "overview"
    assert "api_key" not in report["results"][0]
    with csv_path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
        assert len(rows) == 2
        assert rows[0]["review_focus"] == "overview"
