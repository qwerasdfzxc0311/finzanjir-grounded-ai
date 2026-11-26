# FINZANJIR retrieval diagnostic review — 15 November 2026

## Scope and caveat

This note reviews the read-only artifact produced by workflow run 43689148917 for benchmark `FINZANJIR-QUESTION-DECOMPOSITION-v1`. It contains 12 synthetic cases and 29 subquestions against canonical knowledge corpus v0.6 (8,804 records). It does not call an LLM, bank system, customer data source, or external API. These numbers are a small diagnostic baseline, not a production quality score.

## Verified baseline

- Domain routing: 12/12 cases matched the expected route (100% on this fixture).
- Task-type classification: 12/12 matched (100% on this fixture).
- Expected evidence records: 42.
- Candidate retrieval found 29/42 expected records: 69.05% candidate recall.
- Grounded context admitted 16/42 expected records: 38.10% grounded recall.
- 13 expected records were not found among candidates.
- 245 internal-corpus collision candidates from unknown-scope subquestions were withheld from answer evidence.

The 245 count is not a count of 245 factual errors. It is a count of internal hits that the diagnostic deliberately did not accept as evidence for unknown external, implementation-unverified, or production-unconfirmed questions.

## Per-language evidence results

| Language/script | Expected | Candidate found | Grounded | Candidate recall | Grounded recall |
|---|---:|---:|---:|---:|---:|
| Uzbek Latin | 27 | 17 | 7 | 62.96% | 25.93% |
| Uzbek Cyrillic | 3 | 2 | 1 | 66.67% | 33.33% |
| Russian | 3 | 3 | 3 | 100% | 100% |
| English | 3 | 2 | 2 | 66.67% | 66.67% |
| Kazakh | 3 | 2 | 0 | 66.67% | 0% |
| Karakalpak | 3 | 3 | 3 | 100% | 100% |

The Russian, Kazakh, English, Uzbek Cyrillic, and Karakalpak denominators are only three evidence records each. Their percentages must not be interpreted as stable language capability estimates.

## Main interpretation

1. The small fixture suggests routing is less problematic than evidence retrieval and grounding.
2. Candidate recall and grounded recall must remain separate metrics. A record can be retrieved but still be rejected by the grounding eligibility/relevance gate.
3. Uzbek Latin is the largest measured subgroup and has weak grounded recall (7/27).
4. Kazakh is a clear investigation priority: two expected records appeared among candidates, but none entered grounded context. This is not yet proof of a language-wide failure; the sample is only three expected records.
5. Cross-lingual dictionary hints are retrieval hints, not semantic understanding and not evidence of translation quality.
6. The system correctly withheld unknown-scope hits rather than turning them into unsupported claims. Preserve this safety boundary.

## Diagnostic instrumentation gaps

The current artifact records the top five candidate details while retrieval is configured with a larger candidate pool. It does not make the full per-expected-record rejection path sufficiently transparent. Before tuning thresholds, add a diagnostic-only trace for each expected evidence ID:

- whether it was retrieved and its rank;
- retrieval score and lexical score;
- evidence status and verification state;
- whether the grounding gate admitted it;
- a structured rejection reason (below lexical floor, below retrieval floor, relative relevance filter, unsupported evidence status, or missing record).

This instrumentation should be read-only and must not change production thresholds by itself.

## Safe next sequence

1. Complete the 250+ prompt corpus and remove unintended duplicates against existing QA/decomposition fixtures. Preserve the known typo-normalization regression as an explicitly intentional repeat.
2. Obtain native-speaker review for Kazakh and Karakalpak prompt wording.
3. Map expected evidence only after checking exact canonical source records, provenance, verification status, and query relevance.
4. Add the diagnostic trace described above and rerun the same fixed baseline.
5. Only then test retrieval normalization, concept aliases, candidate ranking, or grounding thresholds against held-out prompts.
6. Do not relax grounding thresholds simply to increase recall. Any change must preserve precision, source eligibility, and the prohibition on treating signals as proof of guilt.

## Change boundary

This review and the prompt batches are benchmark/documentation work only. They do not change runtime routing, the retrieval engine, answer generation, canonical knowledge, API behavior, or Render deployment.
