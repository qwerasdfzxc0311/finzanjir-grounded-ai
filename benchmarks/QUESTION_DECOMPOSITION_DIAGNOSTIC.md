# Question decomposition diagnostic v1

This diagnostic is deliberately separate from the canonical knowledge corpus.

## Run

```bash
python scripts/run_question_decomposition_diagnostic.py
```

Run one case:

```bash
python scripts/run_question_decomposition_diagnostic.py --case CMP-UZ-001
```

Write a local JSON report:

```bash
python scripts/run_question_decomposition_diagnostic.py --output /tmp/finzanjir-question-diagnostic.json
```

## What it measures

- Current intent classifier output versus the benchmark's expected task.
- Per-subquestion lexical retrieval against canonical corpus v0.6.
- Which retrieved records pass the existing evidence-grounding gate.
- Evidence status and verification metadata for manual review.

## What it does not claim

- BM25/IDF scores are not dense semantic similarity.
- Retrieval hits do not prove answer completeness.
- Expected evidence IDs are manually curated for selected internal-knowledge subquestions; unknown external/production/implementation scopes intentionally have no expected internal evidence IDs.
- External comparison claims remain unknown until separate reliable sources are researched and recorded outside the canonical corpus.

No provider, API key, deployment, bank integration, or customer data is used.


## Measured results (2026-11-14)

The read-only diagnostic ran against canonical corpus v0.6 in GitHub Actions.

- Domain routing: 12/12 (100%) were routed to the project domain. This is not task-intent accuracy.
- Separate task-type baseline: 12/12 (100%) on this 12-case fixture. This is an initial synthetic-set result, not an unseen holdout result and not proof of general semantic understanding.
- 42 reviewed expected evidence IDs; baseline top-20 candidate recall 21/42 (50.0%).
- Cross-lingual vocabulary hint top-20 candidate recall 29/42 (69.05%), a +19.05 percentage-point change.
- Grounded expected evidence recall in top-5: 16/42 (38.10%).
- 45 eligible internal grounded candidates, 20 manual-review candidates, and 245 internal-corpus collisions for unknown external/production/implementation scopes. Collisions are not answer evidence.

The report includes full candidate statements, aliases, evidence metadata, and provenance for human review. The original query remains first; the cross-lingual vocabulary bridge adds only a low-priority search hint and never creates evidence. Unknown external systems, production deployment, and unreviewed evidence are not presented as confirmed facts.

## Current implementation boundary

`classify_task_type` and `cross_lingual_query_variants` are separate baseline modules. The diagnostic runner measures them, but the production answer engine has not yet been changed to use either. The vocabulary bridge improved Russian and Karakalpak retrieval and partially helped Kazakh; Uzbek recall and Kazakh grounding remain weak. The next stage requires held-out multilingual/paraphrase tests and an integration test before production routing changes are considered.
