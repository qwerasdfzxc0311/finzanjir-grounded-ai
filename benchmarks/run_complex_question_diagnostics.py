from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from finzanjir_ai.knowledge.index import build_index_from_document
from finzanjir_ai.retrieval.grounding import GroundedContextAssembler
from finzanjir_ai.retrieval.hybrid import HybridRetriever, RetrievalResult
from finzanjir_ai.retrieval.rerank import QueryExpander, Reranker
from finzanjir_ai.retrieval.text import query_script_variants


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BENCHMARK = ROOT / "benchmarks" / "complex_question_benchmark_v1.json"
DEFAULT_CORPUS = ROOT / "data" / "canonical_knowledge_v0.6.json"


def _rank_metrics(ranked_ids: list[str], expected_ids: list[str], top_k: int) -> dict[str, Any]:
    if not expected_ids:
        return {
            "evaluated": False,
            "reason": "no canonical evidence expected for this subquestion",
            "recall_at_k": None,
            "precision_at_k": None,
            "mrr": None,
            "hits": [],
            "missing": [],
        }

    expected = set(expected_ids)
    top = ranked_ids[:top_k]
    hits = [record_id for record_id in top if record_id in expected]
    first_rank = next(
        (rank for rank, record_id in enumerate(ranked_ids, start=1) if record_id in expected),
        None,
    )
    return {
        "evaluated": True,
        "recall_at_k": len(set(hits)) / len(expected),
        "precision_at_k": len(set(hits)) / top_k,
        "mrr": 1.0 / first_rank if first_rank else 0.0,
        "hits": hits,
        "missing": sorted(expected - set(hits)),
        "first_relevant_rank": first_rank,
    }


def _expanded_retrieval(
    query: str,
    *,
    retriever: HybridRetriever,
    expander: QueryExpander,
    reranker: Reranker,
    top_k: int,
) -> tuple[tuple[RetrievalResult, ...], tuple[str, ...]]:
    query_specs: list[tuple[str, float]] = [(query, 2.0)]
    query_specs.extend((value, 0.9) for value in query_script_variants(query)[1:])
    local_queries = expander.expand(query)
    query_specs.extend(
        (value, 1.0)
        for value in local_queries
        if value.strip() and value.strip() != query.strip()
    )

    deduplicated: list[tuple[str, float]] = []
    seen: set[str] = set()
    for value, weight in query_specs:
        key = value.casefold().strip()
        if key and key not in seen:
            seen.add(key)
            deduplicated.append((value, weight))

    fused: dict[str, dict[str, float]] = {}
    total_weight = sum(weight for _, weight in deduplicated) or 1.0
    candidate_limit = max(top_k * 4, 24)
    for search_query, weight in deduplicated:
        for rank, result in enumerate(
            retriever.search(search_query, top_k=candidate_limit),
            start=1,
        ):
            entry = fused.setdefault(
                result.record_id,
                {"rrf": 0.0, "lexical": 0.0},
            )
            entry["rrf"] += weight / (60.0 + rank)
            entry["lexical"] = max(entry["lexical"], result.lexical_score)

    merged = []
    for record_id, values in fused.items():
        normalized_rrf = min(1.0, values["rrf"] * 61.0 / total_weight)
        score = min(1.0, 0.70 * values["lexical"] + 0.30 * normalized_rrf)
        merged.append(
            RetrievalResult(
                record_id=record_id,
                score=score,
                lexical_score=values["lexical"],
                semantic_score=0.0,
            )
        )
    merged.sort(key=lambda item: (-item.score, item.record_id))
    ranked = reranker.rerank(query, tuple(merged))
    alternatives = tuple(value for value, _ in deduplicated[1:])
    return ranked[:top_k], alternatives


def run_diagnostics(
    benchmark: dict[str, Any],
    corpus: dict[str, Any],
    *,
    top_k: int = 10,
) -> dict[str, Any]:
    index = build_index_from_document(corpus)
    retriever = HybridRetriever(index)
    expander = QueryExpander(index)
    reranker = Reranker(index)
    grounder = GroundedContextAssembler(index)
    available_ids = {record.record_id for record in index.records}

    rows: list[dict[str, Any]] = []
    missing_expected_ids: set[str] = set()
    for case in benchmark["cases"]:
        full_query_results = retriever.search(case["query"], top_k=top_k)
        full_query_ids = [item.record_id for item in full_query_results]

        for subquestion in case["subquestions"]:
            expected_ids = subquestion["expected_evidence_ids"]
            missing_expected_ids.update(
                record_id for record_id in expected_ids if record_id not in available_ids
            )
            if not expected_ids:
                rows.append({
                    "case_id": case["id"],
                    "subquestion_id": subquestion["id"],
                    "language": case["language"],
                    "evidence_scope": subquestion["evidence_scope"],
                    "knowledge_state": subquestion["knowledge_state"],
                    "retrieval_query": subquestion["retrieval_query"],
                    "status": "not_scored_no_canonical_evidence_expected",
                })
                continue

            query = subquestion["retrieval_query"]
            baseline = retriever.search(query, top_k=top_k)
            expanded, alternatives = _expanded_retrieval(
                query,
                retriever=retriever,
                expander=expander,
                reranker=reranker,
                top_k=top_k,
            )
            grounded = grounder.assemble(
                expanded,
                query=query,
                query_alternatives=alternatives,
                max_items=top_k,
            )
            baseline_ids = [item.record_id for item in baseline]
            expanded_ids = [item.record_id for item in expanded]
            grounded_ids = [item.record_id for item in grounded.items]

            rows.append({
                "case_id": case["id"],
                "subquestion_id": subquestion["id"],
                "language": case["language"],
                "evidence_scope": subquestion["evidence_scope"],
                "knowledge_state": subquestion["knowledge_state"],
                "retrieval_query": query,
                "expected_evidence_ids": expected_ids,
                "full_question_baseline": _rank_metrics(
                    full_query_ids, expected_ids, top_k
                ),
                "subquestion_baseline": _rank_metrics(
                    baseline_ids, expected_ids, top_k
                ),
                "subquestion_expanded": _rank_metrics(
                    expanded_ids, expected_ids, top_k
                ),
                "subquestion_grounded": _rank_metrics(
                    grounded_ids, expected_ids, top_k
                ),
                "ranked_ids": {
                    "baseline": baseline_ids,
                    "expanded": expanded_ids,
                    "grounded": grounded_ids,
                },
            })

    scored = [row for row in rows if row.get("status") is None]
    def aggregate(metric_name: str, stage: str) -> dict[str, Any]:
        values = [
            row[stage][metric_name]
            for row in scored
            if row[stage]["evaluated"]
        ]
        return {
            "mean": sum(values) / len(values) if values else None,
            "count": len(values),
        }

    return {
        "benchmark_id": benchmark["benchmark_id"],
        "benchmark_version": benchmark["version"],
        "corpus_version": benchmark["corpus_version"],
        "diagnostic_scope": "retrieval_only_with_oracle_subquestion_decomposition",
        "not_measured": [
            "runtime intent classification",
            "automatic question decomposition",
            "answer composition or completeness",
            "external web comparison quality",
            "live browser/API behavior",
        ],
        "top_k": top_k,
        "case_count": len(benchmark["cases"]),
        "scored_subquestion_count": len(scored),
        "unscored_subquestion_count": len(rows) - len(scored),
        "missing_expected_record_ids": sorted(missing_expected_ids),
        "aggregate": {
            stage: {
                metric: aggregate(metric, stage)
                for metric in ("recall_at_k", "precision_at_k", "mrr")
            }
            for stage in (
                "full_question_baseline",
                "subquestion_baseline",
                "subquestion_expanded",
                "subquestion_grounded",
            )
        },
        "results": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run keyless retrieval diagnostics using oracle subquestion fixtures."
    )
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    benchmark = json.loads(args.benchmark.read_text(encoding="utf-8"))
    corpus = json.loads(args.corpus.read_text(encoding="utf-8"))
    report = run_diagnostics(benchmark, corpus, top_k=args.top_k)
    rendered = json.dumps(report, ensure_ascii=False, indent=2)

    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
