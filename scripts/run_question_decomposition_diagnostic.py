from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from finzanjir_ai.knowledge.index import build_index_from_document
from finzanjir_ai.knowledge.loader import load_canonical_knowledge
from finzanjir_ai.orchestration.intent import classify_query_intent
from finzanjir_ai.orchestration.task_intent import classify_task_type
from finzanjir_ai.retrieval.cross_lingual import cross_lingual_query_variants, translate_search_hint
from finzanjir_ai.retrieval.grounding import GroundedContextAssembler
from finzanjir_ai.retrieval.hybrid import HybridRetriever, RetrievalResult
from finzanjir_ai.retrieval.rerank import QueryExpander, Reranker
from finzanjir_ai.retrieval.text import query_script_variants


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "benchmarks" / "question_decomposition_diagnostic_v1.json"
ANSWERABLE_STATUSES = {"known_in_corpus", "known_or_partial_in_corpus"}
REVIEW_ONLY_STATUSES = {"unknown_until_evidence_review"}
NON_EVIDENCE_STATUSES = {
    "unknown_external",
    "unknown_until_production_evidence",
    "unknown_until_implementation_evidence",
}


def retrieve_candidates(
    question: str,
    retriever: HybridRetriever,
    top_k: int,
    *,
    variants: tuple[str, ...] | None = None,
) -> list[dict[str, Any]]:
    """Fuse query variants for ranking while preserving original retriever scores."""
    fused: dict[str, dict[str, Any]] = {}
    for variant_rank, variant in enumerate(variants or query_script_variants(question)):
        for rank, hit in enumerate(retriever.search(variant, top_k=top_k * 4), start=1):
            row = fused.setdefault(
                hit.record_id,
                {"rrf_score": 0.0, "best_hit": hit},
            )
            row["rrf_score"] += (1.0 / (60.0 + rank)) / (variant_rank + 1)
            best = row["best_hit"]
            if hit.score > best.score:
                row["best_hit"] = hit

    ranked = sorted(
        fused.items(),
        key=lambda pair: (-pair[1]["rrf_score"], -pair[1]["best_hit"].score, pair[0]),
    )
    return [
        {
            "record_id": record_id,
            "rrf_score": round(values["rrf_score"], 6),
            "retrieval_score": values["best_hit"].score,
            "lexical_score": values["best_hit"].lexical_score,
        }
        for record_id, values in ranked[:top_k]
    ]


def diagnose_case(
    case: dict[str, Any],
    index: Any,
    retriever: HybridRetriever,
    grounder: GroundedContextAssembler,
    expander: QueryExpander,
    reranker: Reranker,
    top_k: int = 5,
) -> dict[str, Any]:
    query = case["query"]
    actual_domain_route = classify_query_intent(query)
    actual_task_type = classify_task_type(query)
    subresults = []
    record_map = {record.record_id: record for record in index.records}

    for subquestion in case["subquestions"]:
        question = subquestion["question"]
        status = subquestion["knowledge_status"]
        script_variants = query_script_variants(question)
        baseline_candidates = retrieve_candidates(
            question, retriever, top_k * 4, variants=script_variants
        )
        bridge_variants = cross_lingual_query_variants(question)
        translation_hint, translated_term_count = translate_search_hint(question)
        bridge_candidates = retrieve_candidates(
            question, retriever, top_k * 4, variants=bridge_variants
        )
        local_variants = expander.expand(question)
        local_expanded_variants = tuple(dict.fromkeys(
            (*bridge_variants, *local_variants)
        ))
        candidates = retrieve_candidates(
            question, retriever, top_k * 4, variants=local_expanded_variants
        )

        candidate_details = []
        for candidate in candidates[:top_k]:
            record = record_map.get(candidate["record_id"])
            candidate_details.append({
                **candidate,
                "statement": record.statement if record else "",
                "aliases": list(record.aliases) if record else [],
                "evidence_status": (
                    record.evidence.get("status")
                    if record and isinstance(record.evidence, dict) else None
                ),
                "verification": (
                    record.evidence.get("verification")
                    if record and isinstance(record.evidence, dict) else None
                ),
                "provenance": list(record.provenance) if record else [],
                "evidence_metadata": record.evidence if record else None,
            })

        if status in ANSWERABLE_STATUSES:
            retrieval_results = tuple(
                RetrievalResult(
                    record_id=item["record_id"],
                    score=item["retrieval_score"],
                    lexical_score=item["lexical_score"],
                    semantic_score=0.0,
                )
                for item in candidates
            )
            reranked = reranker.rerank(question, retrieval_results)
            grounded = grounder.assemble(
                reranked,
                query=question,
                query_alternatives=tuple(
                    value for value in local_expanded_variants if value.strip() != question.strip()
                ),
                max_items=top_k,
            )
            evidence_ids = [item.record_id for item in grounded.items]
            disposition = "eligible_internal_evidence_candidates"
            review_ids: list[str] = []
            collision_ids: list[str] = []
        elif status in REVIEW_ONLY_STATUSES:
            evidence_ids = []
            review_ids = [item["record_id"] for item in candidates]
            collision_ids = []
            disposition = "candidate_records_require_manual_evidence_review"
        elif status in NON_EVIDENCE_STATUSES:
            evidence_ids = []
            review_ids = []
            collision_ids = [item["record_id"] for item in candidates]
            disposition = "internal_hits_are_not_evidence_for_this_unknown_scope"
        else:
            evidence_ids = []
            review_ids = [item["record_id"] for item in candidates]
            collision_ids = []
            disposition = "unrecognized_knowledge_status_requires_review"

        expected_ids = subquestion.get("evidence_ids", [])
        candidate_ids = [item["record_id"] for item in candidates]
        baseline_candidate_ids = [item["record_id"] for item in baseline_candidates]
        bridge_candidate_ids = [item["record_id"] for item in bridge_candidates]
        baseline_retrieved_expected_ids = [
            item for item in expected_ids if item in baseline_candidate_ids
        ]
        bridge_retrieved_expected_ids = [
            item for item in expected_ids if item in bridge_candidate_ids
        ]
        retrieved_expected_ids = [item for item in expected_ids if item in candidate_ids]
        grounded_expected_ids = [item for item in expected_ids if item in evidence_ids]
        missed_expected_ids = [item for item in expected_ids if item not in candidate_ids]
        expected_record_details = [
            {
                "record_id": record_id,
                "statement": record_map[record_id].statement,
                "aliases": list(record_map[record_id].aliases),
                "evidence_status": (
                    record_map[record_id].evidence.get("status")
                    if isinstance(record_map[record_id].evidence, dict) else None
                ),
                "provenance": list(record_map[record_id].provenance),
            }
            for record_id in expected_ids if record_id in record_map
        ]

        subresults.append({
            "subquestion_id": subquestion["id"],
            "question": question,
            "declared_knowledge_status": status,
            "required_action": subquestion["required_action"],
            "query_language": case["language"],
            "script_query_variants": list(script_variants),
            "cross_lingual_query_variants": list(bridge_variants),
            "local_query_expansion_variants": list(local_variants),
            "query_variants": list(local_expanded_variants),
            "translation_hint": translation_hint,
            "translated_term_count": translated_term_count,
            "baseline_retrieved_expected_evidence_ids": baseline_retrieved_expected_ids,
            "bridge_retrieved_expected_evidence_ids": bridge_retrieved_expected_ids,
            "expected_evidence_ids": expected_ids,
            "expected_evidence_record_details": expected_record_details,
            "retrieved_expected_evidence_ids": retrieved_expected_ids,
            "grounded_expected_evidence_ids": grounded_expected_ids,
            "missed_expected_evidence_ids": missed_expected_ids,
            "baseline_expected_evidence_candidate_recall": (
                round(len(baseline_retrieved_expected_ids) / len(expected_ids), 4) if expected_ids else None
            ),
            "bridge_expected_evidence_candidate_recall": (
                round(len(bridge_retrieved_expected_ids) / len(expected_ids), 4) if expected_ids else None
            ),
            "expected_evidence_candidate_recall": (
                round(len(retrieved_expected_ids) / len(expected_ids), 4) if expected_ids else None
            ),
            "expected_evidence_grounded_recall": (
                round(len(grounded_expected_ids) / len(expected_ids), 4) if expected_ids else None
            ),
            "evidence_disposition": disposition,
            "eligible_grounded_record_ids": evidence_ids,
            "candidate_records_for_manual_review": review_ids,
            "internal_corpus_collision_record_ids": collision_ids,
            "top_hits": candidate_details,
        })

    return {
        "case_id": case["id"],
        "query": query,
        "expected_domain_route": case["expected_domain_route"],
        "actual_domain_route": actual_domain_route,
        "domain_route_match": actual_domain_route == case["expected_domain_route"],
        "expected_task_type": case["expected_task_type"],
        "actual_task_type": actual_task_type,
        "task_type_match": actual_task_type == case["expected_task_type"],
        "subquestions": subresults,
        "diagnostic_only": True,
        "note": (
            "The current intent classifier routes domain (project/general/author), not task type. "
            "Lexical retrieval scores are not semantic similarity. Unknown-scope internal hits "
            "are explicitly excluded from eligible answer evidence."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run FINZANJIR question decomposition retrieval diagnostics."
    )
    parser.add_argument(
        "--corpus",
        type=Path,
        default=ROOT / "data" / "canonical_knowledge_v0.6.json",
    )
    parser.add_argument("--case", help="Optional exact case ID.")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--output", type=Path, help="Optional JSON report path.")
    args = parser.parse_args()

    benchmark = json.loads(FIXTURE.read_text(encoding="utf-8"))
    cases = [
        case for case in benchmark["cases"]
        if not args.case or case["id"] == args.case
    ]
    if not cases:
        parser.error(f"No benchmark case found for --case {args.case!r}")

    document = load_canonical_knowledge(args.corpus)
    index = build_index_from_document(document)
    retriever = HybridRetriever(index)
    grounder = GroundedContextAssembler(index)
    expander = QueryExpander(index)
    reranker = Reranker(index)

    report: dict[str, Any] = {
        "benchmark_id": benchmark["benchmark_id"],
        "corpus_version": benchmark["corpus_version"],
        "case_count": len(cases),
        "subquestion_count": sum(len(case["subquestions"]) for case in cases),
        "candidate_retrieval_top_n": args.top_k * 4,
        "domain_route_matches": 0,
        "domain_route_mismatches": [],
        "task_type_classifier_status": "baseline_implemented_for_diagnostic",
        "task_type_matches": 0,
        "task_type_mismatches": [],
        "cases": [],
        "limitations": [
            "This runner measures domain routing and per-subquestion lexical retrieval only.",
            "Task-type classification is a separate multilingual baseline and is evaluated independently from domain routing.",
            "It does not call an LLM, external API, browser, bank system, or customer data source.",
            "Only known/partial internal-knowledge subquestions can produce eligible grounded candidates.",
            "The report compares original/script-only retrieval, cross-lingual bridge retrieval, and local query-expansion retrieval separately.",
            "Local query expansion, cross-lingual variants, and model-proposed rewrites are search hints only; none is evidence.",
            "External, production-unconfirmed, implementation-unverified, and manual-review-only hits are not counted as answer evidence.",
            "Expected evidence IDs remain subject to human provenance and relevance review.",
        ],
    }

    for case in cases:
        result = diagnose_case(case, index, retriever, grounder, expander, reranker, top_k=args.top_k)
        report["cases"].append(result)
        if result["domain_route_match"]:
            report["domain_route_matches"] += 1
        else:
            report["domain_route_mismatches"].append({
                "case_id": result["case_id"],
                "expected": result["expected_domain_route"],
                "actual": result["actual_domain_route"],
            })
        if result["task_type_match"]:
            report["task_type_matches"] += 1
        else:
            report["task_type_mismatches"].append({
                "case_id": result["case_id"],
                "expected": result["expected_task_type"],
                "actual": result["actual_task_type"],
            })

    report["task_type_accuracy"] = round(report["task_type_matches"] / len(cases), 4)
    report["domain_route_accuracy"] = round(
        report["domain_route_matches"] / len(cases), 4
    )
    expected_subquestions = [
        sub for case in report["cases"] for sub in case["subquestions"]
        if sub["expected_evidence_ids"]
    ]
    expected_total = sum(len(sub["expected_evidence_ids"]) for sub in expected_subquestions)
    baseline_retrieved_expected_total = sum(len(sub["baseline_retrieved_expected_evidence_ids"]) for sub in expected_subquestions)
    bridge_retrieved_expected_total = sum(len(sub["bridge_retrieved_expected_evidence_ids"]) for sub in expected_subquestions)
    retrieved_expected_total = sum(len(sub["retrieved_expected_evidence_ids"]) for sub in expected_subquestions)
    grounded_expected_total = sum(len(sub["grounded_expected_evidence_ids"]) for sub in expected_subquestions)
    language_totals: dict[str, dict[str, int]] = {}
    for sub in expected_subquestions:
        language = sub["query_language"]
        totals = language_totals.setdefault(language, {
            "expected": 0,
            "baseline_retrieved": 0,
            "bridge_retrieved": 0,
            "local_expansion_retrieved": 0,
            "grounded": 0,
        })
        totals["expected"] += len(sub["expected_evidence_ids"])
        totals["baseline_retrieved"] += len(sub["baseline_retrieved_expected_evidence_ids"])
        totals["bridge_retrieved"] += len(sub["bridge_retrieved_expected_evidence_ids"])
        totals["local_expansion_retrieved"] += len(sub["retrieved_expected_evidence_ids"])
        totals["grounded"] += len(sub["grounded_expected_evidence_ids"])
    report["language_metrics"] = {
        language: {
            **totals,
            "baseline_candidate_recall": round(totals["baseline_retrieved"] / totals["expected"], 4),
            "bridge_candidate_recall": round(totals["bridge_retrieved"] / totals["expected"], 4),
            "local_expansion_candidate_recall": round(totals["local_expansion_retrieved"] / totals["expected"], 4),
            "grounded_recall": round(totals["grounded"] / totals["expected"], 4),
        }
        for language, totals in language_totals.items()
    }
    report["expected_evidence_total"] = expected_total
    report["baseline_retrieved_expected_evidence_total"] = baseline_retrieved_expected_total
    report["baseline_expected_evidence_candidate_recall"] = round(baseline_retrieved_expected_total / expected_total, 4) if expected_total else None
    report["bridge_retrieved_expected_evidence_total"] = bridge_retrieved_expected_total
    report["bridge_expected_evidence_candidate_recall"] = round(bridge_retrieved_expected_total / expected_total, 4) if expected_total else None
    report["retrieved_expected_evidence_total"] = retrieved_expected_total
    report["grounded_expected_evidence_total"] = grounded_expected_total
    report["missed_expected_evidence_total"] = expected_total - retrieved_expected_total
    report["expected_evidence_candidate_recall"] = round(retrieved_expected_total / expected_total, 4) if expected_total else None
    report["expected_evidence_grounded_recall"] = round(grounded_expected_total / expected_total, 4) if expected_total else None
    report["eligible_evidence_count"] = sum(
        len(sub["eligible_grounded_record_ids"])
        for case in report["cases"]
        for sub in case["subquestions"]
    )
    report["manual_review_candidate_count"] = sum(
        len(sub["candidate_records_for_manual_review"])
        for case in report["cases"]
        for sub in case["subquestions"]
    )
    report["internal_collision_count"] = sum(
        len(sub["internal_corpus_collision_record_ids"])
        for case in report["cases"]
        for sub in case["subquestions"]
    )

    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
