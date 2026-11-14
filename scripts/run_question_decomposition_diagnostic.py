from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from finzanjir_ai.knowledge.index import build_index_from_document
from finzanjir_ai.knowledge.loader import load_canonical_knowledge
from finzanjir_ai.orchestration.intent import classify_query_intent
from finzanjir_ai.orchestration.task_intent import classify_task_type
from finzanjir_ai.retrieval.grounding import GroundedContextAssembler
from finzanjir_ai.retrieval.hybrid import HybridRetriever, RetrievalResult
from finzanjir_ai.retrieval.text import query_script_variants


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "benchmarks" / "question_decomposition_diagnostic_v1.json"
ANSWERABLE_STATUSES = {"known_in_corpus", "known_or_partial_in_corpus"}
REVIEW_ONLY_STATUSES = {"unknown_until_evidence_review"}
NON_EVIDENCE_STATUSES = {
    "unknown_external",
    "unknown_until_production_evidence",
}


def retrieve_candidates(question: str, retriever: HybridRetriever, top_k: int) -> list[dict[str, Any]]:
    """Fuse script variants for ranking while preserving original retriever scores."""
    fused: dict[str, dict[str, Any]] = {}
    for variant_rank, variant in enumerate(query_script_variants(question)):
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
        candidates = retrieve_candidates(question, retriever, top_k * 4)

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
            grounded = grounder.assemble(
                retrieval_results,
                query=question,
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

        subresults.append({
            "subquestion_id": subquestion["id"],
            "question": question,
            "declared_knowledge_status": status,
            "required_action": subquestion["required_action"],
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

    report: dict[str, Any] = {
        "benchmark_id": benchmark["benchmark_id"],
        "corpus_version": benchmark["corpus_version"],
        "case_count": len(cases),
        "subquestion_count": sum(len(case["subquestions"]) for case in cases),
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
            "External, production-unconfirmed, and manual-review-only hits are not counted as answer evidence.",
            "Expected evidence IDs remain subject to human provenance and relevance review.",
        ],
    }

    for case in cases:
        result = diagnose_case(case, index, retriever, grounder, top_k=args.top_k)
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
