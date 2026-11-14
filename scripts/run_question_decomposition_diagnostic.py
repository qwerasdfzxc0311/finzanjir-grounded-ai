from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from finzanjir_ai.knowledge.index import build_index_from_document
from finzanjir_ai.knowledge.loader import load_canonical_knowledge
from finzanjir_ai.orchestration.intent import classify_query_intent
from finzanjir_ai.retrieval.grounding import GroundedContextAssembler
from finzanjir_ai.retrieval.hybrid import HybridRetriever
from finzanjir_ai.retrieval.text import query_script_variants


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "benchmarks" / "question_decomposition_diagnostic_v1.json"


def diagnose_case(case: dict[str, Any], index: Any, top_k: int = 5) -> dict[str, Any]:
    retriever = HybridRetriever(index)
    grounder = GroundedContextAssembler(index)
    query = case["query"]
    intent = classify_query_intent(query)
    subresults = []

    for subquestion in case["subquestions"]:
        question = subquestion["question"]
        variants = query_script_variants(question)
        fused: dict[str, dict[str, float]] = {}
        for variant_rank, variant in enumerate(variants):
            for rank, hit in enumerate(retriever.search(variant, top_k=top_k * 4), start=1):
                row = fused.setdefault(hit.record_id, {"score": 0.0, "lexical_score": 0.0})
                row["score"] += (1.0 / (60.0 + rank)) / (variant_rank + 1)
                row["lexical_score"] = max(row["lexical_score"], hit.lexical_score)

        ranked = sorted(
            fused.items(),
            key=lambda pair: (-pair[1]["score"], -pair[1]["lexical_score"], pair[0]),
        )
        from finzanjir_ai.retrieval.hybrid import RetrievalResult
        retrieval_results = tuple(
            RetrievalResult(
                record_id=record_id,
                score=min(1.0, values["score"] * 61.0),
                lexical_score=values["lexical_score"],
                semantic_score=0.0,
            )
            for record_id, values in ranked
        )
        grounded = grounder.assemble(retrieval_results, query=question, max_items=top_k)
        grounded_ids = [item.record_id for item in grounded.items]
        top_hits = []
        for record_id, values in ranked[:top_k]:
            record = index.get_record(record_id)
            top_hits.append({
                "record_id": record_id,
                "score": round(values["score"], 6),
                "lexical_score": round(values["lexical_score"], 6),
                "grounded": record_id in grounded_ids,
                "statement_preview": (record.statement[:260] if record else ""),
                "evidence_status": (
                    record.evidence.get("status")
                    if record and isinstance(record.evidence, dict) else None
                ),
                "verification": (
                    record.evidence.get("verification")
                    if record and isinstance(record.evidence, dict) else None
                ),
            })

        subresults.append({
            "subquestion_id": subquestion["id"],
            "question": question,
            "declared_knowledge_status": subquestion["knowledge_status"],
            "required_action": subquestion["required_action"],
            "grounded_evidence_count": len(grounded_ids),
            "grounded_record_ids": grounded_ids,
            "top_hits": top_hits,
        })

    return {
        "case_id": case["id"],
        "query": query,
        "expected_intent": case["expected_intent"],
        "actual_intent": intent,
        "intent_match": intent == case["expected_intent"],
        "task_type": case["task_type"],
        "subquestions": subresults,
        "diagnostic_only": True,
        "note": "Lexical retrieval diagnostic; scores are not semantic similarity and do not constitute answer-quality evaluation."
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run FINZANJIR question decomposition retrieval diagnostics.")
    parser.add_argument("--corpus", type=Path, default=ROOT / "data" / "canonical_knowledge_v0.6.json")
    parser.add_argument("--case", help="Optional exact case ID.")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--output", type=Path, help="Optional JSON report path.")
    args = parser.parse_args()

    benchmark = json.loads(FIXTURE.read_text(encoding="utf-8"))
    cases = [case for case in benchmark["cases"] if not args.case or case["id"] == args.case]
    if not cases:
        parser.error(f"No benchmark case found for --case {args.case!r}")

    document = load_canonical_knowledge(args.corpus)
    index = build_index_from_document(document)
    report = {
        "benchmark_id": benchmark["benchmark_id"],
        "corpus_version": benchmark["corpus_version"],
        "case_count": len(cases),
        "intent_matches": 0,
        "intent_mismatches": [],
        "cases": [],
        "limitations": [
            "This runner measures intent routing and per-subquestion lexical evidence retrieval only.",
            "It does not call an LLM, external API, browser, bank system, or customer data source.",
            "It does not claim that retrieved records form a complete answer.",
            "Expected evidence IDs must be curated after inspecting the returned record IDs and source provenance."
        ]
    }
    for case in cases:
        result = diagnose_case(case, index, top_k=args.top_k)
        report["cases"].append(result)
        if result["intent_match"]:
            report["intent_matches"] += 1
        else:
            report["intent_mismatches"].append({
                "case_id": result["case_id"],
                "expected": result["expected_intent"],
                "actual": result["actual_intent"]
            })
    report["intent_accuracy"] = round(report["intent_matches"] / len(cases), 4)
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
