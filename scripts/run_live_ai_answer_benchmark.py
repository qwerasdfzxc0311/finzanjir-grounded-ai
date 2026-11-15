from __future__ import annotations

import argparse
import csv
import json
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx


DEFAULT_BENCHMARK = Path(__file__).resolve().parents[1] / "benchmarks" / "live_ai_answer_qa_v1.json"


def summarize_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    provider_statuses = Counter(
        str(row.get("provider_status") or "missing") for row in results
    )
    generation_modes = Counter(
        str(row.get("generation_mode") or "missing") for row in results
    )
    failure_categories: Counter[str] = Counter()
    for row in results:
        diagnostics = row.get("provider_diagnostics")
        if not isinstance(diagnostics, list):
            continue
        for item in diagnostics:
            if isinstance(item, dict):
                provider = str(item.get("provider") or "unknown")
                category = str(item.get("status") or "unknown")
                failure_categories[f"{provider}:{category}"] += 1

    return {
        "total": len(results),
        "http_2xx": sum(
            1 for row in results
            if isinstance(row.get("http_status"), int) and 200 <= row["http_status"] < 300
        ),
        "json_responses": sum(1 for row in results if row.get("json_returned") is True),
        "nonempty_answers": sum(1 for row in results if row.get("answer_nonempty") is True),
        "abstentions": sum(1 for row in results if row.get("abstained") is True),
        "provider_status_counts": dict(sorted(provider_statuses.items())),
        "generation_mode_counts": dict(sorted(generation_modes.items())),
        "provider_failure_categories": dict(sorted(failure_categories.items())),
    }


def _result_from_response(
    question: dict[str, Any],
    status_code: int,
    payload: Any,
) -> dict[str, Any]:
    body = payload if isinstance(payload, dict) else {}
    answer = body.get("answer")
    answer_text = answer if isinstance(answer, str) else ""
    diagnostics = body.get("provider_diagnostics")
    if not isinstance(diagnostics, list):
        diagnostics = []
    refs = body.get("knowledge_refs")
    if not isinstance(refs, list):
        refs = []
    provenance = body.get("provenance")
    if not isinstance(provenance, list):
        provenance = []

    return {
        "id": question["id"],
        "question": question["question"],
        "expected_language": question["language"],
        "topic": question["topic"],
        "review_focus": question.get("review_focus", ""),
        "http_status": status_code,
        "json_returned": isinstance(payload, dict),
        "answer_nonempty": bool(answer_text.strip()),
        "answer": answer_text,
        "abstained": body.get("abstained"),
        "generation_mode": body.get("generation_mode"),
        "provider_status": body.get("provider_status"),
        "provider_diagnostics": diagnostics,
        "confidence": body.get("confidence"),
        "knowledge_refs": refs,
        "provenance": provenance,
        "error_type": None,
    }


def run_benchmark(
    *,
    base_url: str,
    benchmark_path: Path = DEFAULT_BENCHMARK,
    output_dir: Path = Path("outputs/live-ai-benchmark"),
    timeout_seconds: float = 45.0,
    delay_ms: int = 1200,
    max_questions: int | None = None,
) -> dict[str, Any]:
    benchmark = json.loads(benchmark_path.read_text(encoding="utf-8"))
    questions = benchmark["questions"]
    if max_questions is not None:
        questions = questions[:max_questions]

    endpoint = base_url.rstrip("/") + "/api/ai/answer"
    results: list[dict[str, Any]] = []
    started_at = datetime.now(timezone.utc).isoformat()

    with httpx.Client(timeout=timeout_seconds) as client:
        for index, question in enumerate(questions):
            try:
                response = client.post(endpoint, json={"question": question["question"]})
                try:
                    payload = response.json()
                except ValueError:
                    payload = None
                result = _result_from_response(question, response.status_code, payload)
            except httpx.HTTPError as exc:
                result = {
                    "id": question["id"],
                    "question": question["question"],
                    "expected_language": question["language"],
                    "topic": question["topic"],
                    "review_focus": question.get("review_focus", ""),
                    "http_status": None,
                    "json_returned": False,
                    "answer_nonempty": False,
                    "answer": "",
                    "abstained": None,
                    "generation_mode": None,
                    "provider_status": None,
                    "provider_diagnostics": [],
                    "confidence": None,
                    "knowledge_refs": [],
                    "provenance": [],
                    "error_type": type(exc).__name__,
                }
            results.append(result)
            if delay_ms > 0 and index < len(questions) - 1:
                time.sleep(delay_ms / 1000)

    finished_at = datetime.now(timezone.utc).isoformat()
    summary = summarize_results(results)
    report = {
        "benchmark_id": benchmark["benchmark_id"],
        "benchmark_version": benchmark["version"],
        "base_url": base_url.rstrip("/"),
        "endpoint": endpoint,
        "corpus_version": benchmark.get("corpus_version"),
        "started_at": started_at,
        "finished_at": finished_at,
        "summary": summary,
        "results": results,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "live_ai_answer_results.json"
    csv_path = output_dir / "live_ai_answer_results.csv"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    columns = [
        "id", "question", "expected_language", "topic", "review_focus", "http_status",
        "json_returned", "answer_nonempty", "abstained", "generation_mode",
        "provider_status", "provider_diagnostics", "confidence", "knowledge_refs",
        "provenance", "error_type", "answer",
    ]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in results:
            flat = dict(row)
            for key in ("provider_diagnostics", "knowledge_refs", "provenance"):
                flat[key] = json.dumps(flat.get(key) or [], ensure_ascii=False)
            writer.writerow({key: flat.get(key) for key in columns})

    return {
        "summary": summary,
        "json_path": str(json_path),
        "csv_path": str(csv_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the synthetic 50-question FINZANJIR AI answer benchmark."
    )
    parser.add_argument("--base-url", required=True, help="Base URL of the FINZANJIR API.")
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/live-ai-benchmark"))
    parser.add_argument("--timeout-seconds", type=float, default=45.0)
    parser.add_argument("--delay-ms", type=int, default=1200)
    parser.add_argument("--max-questions", type=int, default=None)
    args = parser.parse_args()

    result = run_benchmark(
        base_url=args.base_url,
        benchmark_path=args.benchmark,
        output_dir=args.output_dir,
        timeout_seconds=args.timeout_seconds,
        delay_ms=args.delay_ms,
        max_questions=args.max_questions,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
