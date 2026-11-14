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
- The fixture's expected evidence ID arrays are intentionally empty until a human reviews the diagnostic output and confirms exact record IDs and provenance.
- External comparison claims remain unknown until separate reliable sources are researched and recorded outside the canonical corpus.

No provider, API key, deployment, bank integration, or customer data is used.


## Measured results (2026-11-14)

The read-only diagnostic ran against canonical corpus v0.6 in GitHub Actions.

- Domain routing: 12/12 (100%) were routed to the project domain. This is not task-intent accuracy.
- Separate task-type baseline: 12/12 (100%) on this 12-case fixture. This is an initial synthetic-set result, not an unseen holdout result and not proof of general semantic understanding.
- Internal grounded candidates for answerable/partial subquestions: 44.
- Candidate records requiring manual evidence review: 20.
- Internal-corpus collision candidates for unknown external/production scopes: 225. These are deliberately excluded from answer evidence.

The report includes full candidate statements, aliases, evidence metadata, and provenance for human review. Unknown external systems, production deployment, and unreviewed evidence are not presented as confirmed facts.

## Current implementation boundary

`classify_task_type` is a separate multilingual baseline module. The diagnostic runner measures it, but the production answer engine has not yet been changed to use it. The next stage requires a held-out paraphrase set, reviewed expected evidence IDs, and an integration test before routing changes are considered.
