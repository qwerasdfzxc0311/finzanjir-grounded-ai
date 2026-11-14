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
