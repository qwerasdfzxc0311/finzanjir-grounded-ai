# FINZANJIR AI benchmark expansion plan — 250 prompts (v1)

## Decision

FINZANJIR must not be constrained to a small FAQ or a handful of canned answers. The evaluation set will grow to **at least 250 distinct user prompts**, with multi-part decomposition cases and controlled paraphrase variants. The count is a minimum evaluation floor, not a limit on the number of questions the AI can answer.

This is a benchmark plan, not a claim that retrieval or answer quality already meets the targets. No runtime behavior changes are included here.

## Existing baseline assets

- `benchmarks/live_ai_answer_qa_v1.json`: 50 synthetic end-to-end QA prompts.
- `benchmarks/complex_question_benchmark_v1.json`: 8 complex cases / 18 subquestions.
- `benchmarks/question_decomposition_diagnostic_v1.json`: 12 diagnostic cases / 29 subquestions.
- Canonical knowledge corpus v0.6: 8,804 records. It remains read-only and authoritative.

These datasets overlap in purpose and must not simply be added together and reported as 70 unique prompts. The expansion process must deduplicate semantically and retain provenance.

## Proposed language/script coverage (250 unique prompts)

| Language/script | Minimum prompts | Coverage notes |
|---|---:|---|
| Uzbek Latin | 100 | Main usage, colloquial phrasing, spelling variants, apostrophe/no-apostrophe, typos |
| Uzbek Cyrillic | 25 | Script conversion, colloquial forms, mixed script |
| Russian | 35 | Natural phrasing, inflection, abbreviations, multi-part questions |
| English | 30 | Technical vocabulary and ordinary user questions |
| Kazakh | 30 | Cyrillic and common FINZANJIR technical terms |
| Karakalpak | 30 | Latin/Cyrillic variants where corpus support exists; native review required |
| **Total** | **250** | |

Do not translate all questions mechanically. Each language set must contain naturally phrased questions reviewed by a competent speaker. If a language's canonical evidence or translation is not verified, mark the test as a language/evidence gap rather than inventing a gold answer.

## Coverage matrix

The 250 prompts should cover these families. Counts are planning targets and can be adjusted after corpus audit; the total must remain at least 250.

1. Project identity, purpose, origin, author motivation and philosophy — 20
2. Core concepts: signal, risk score, Case, Fraud Graph, Cross-Match, knowledge tree — 25
3. Fraud patterns, linked transactions, multiple cards, device/network and phishing — 25
4. Architecture, 16 layers, C model, modules and data flow — 25
5. User protection, lawful transfers, false positives/negatives, human review and appeals — 25
6. Privacy, data minimization, retention, access control, secrecy and interbank exchange — 25
7. Legal basis, Central Bank/bank authority, regulator processes and unresolved legal questions — 20
8. Current implementation vs prototype vs proposal vs production status — 20
9. Pilot design, evaluation, KPIs, operational readiness and evidence — 15
10. Recovery, incident response, complaint handling and limits — 10
11. AI behavior: evidence, citations, uncertainty, unsupported questions, general knowledge separation — 15
12. Technical operation, deployment, troubleshooting and roadmap — 10
13. Adversarial, misleading, mixed-intent and near-miss questions — 15
14. General-knowledge questions outside FINZANJIR domain — 5
15. Author-name/opinion traps and other context-confusion tests — 5
**Total: 250**

## Prompt types inside each family

Use a balanced mix rather than repeating the same sentence with different words:

- Direct definition and purpose questions.
- "How does it work?" process questions with multiple steps.
- Why/how/when/for-whom explanatory questions.
- Multi-part questions that require decomposition and partial answers.
- Follow-up questions that depend on conversation context.
- Colloquial Uzbek, typos, phonetic spellings, omitted apostrophes and mixed-language terms.
- Paraphrases and synonyms that should reach the same evidence without becoming fixed-answer triggers.
- Comparison questions where internal facts can be answered but unsupported external comparisons must be withheld.
- Status questions distinguishing concept, prototype, code, pilot and production.
- Unknown-answer questions where the correct behavior is to disclose the evidence gap.
- Negative/adversarial questions that try to elicit false guarantees, automatic blocking, guilt attribution, bank blame or invented integrations.
- General-knowledge questions that must not be forced into FINZANJIR project mode.

## Three answer modes under evaluation

1. **Canonical deterministic** — only a narrow allowlist of approved stable answers. Exact/semantic intent plus required evidence IDs are mandatory. A keyword match alone is insufficient.
2. **Grounded generative** — default for ordinary FINZANJIR project questions. Decompose the question, retrieve evidence for each part, explain and synthesize supported facts, and label plans/unknowns.
3. **Abstain / partial answer / clarify** — answer supported parts, identify missing evidence for unsupported parts, and ask a focused clarification only when needed.

General knowledge remains a separate domain. External research is labelled as external and never silently promoted to project fact.

## Scoring and release gates

Measure separately:
- Intent and domain routing accuracy.
- Task-type classification and multi-intent decomposition accuracy.
- Evidence Recall@5 and Recall@10 per subquestion.
- Grounded evidence coverage per answerable subquestion.
- Citation precision and source relevance.
- Answer completeness and relevance.
- Unsupported-claim rate.
- Correct partial-answer and abstention rate.
- Language/script match and naturalness.
- False deterministic-trigger rate on near-miss questions.
- Latency, token use and provider cost.

Do not hide weak subgroups behind a high aggregate score. Report every language/script and task family separately. A release candidate must not regress any safety-critical subgroup.

## Current diagnostic baseline — important finding

The 15 November 2026 read-only diagnostic used 12 synthetic cases / 29 subquestions. Domain routing and task-type baseline were each 12/12 on this small fixture, but that does **not** establish generalization.

Evidence retrieval was weak:
- Expected evidence: 42 records.
- Candidate retrieval recall: 29/42 = 69.05%.
- Grounded evidence recall: 16/42 = 38.10%.
- Uzbek Latin grounded recall: 7/27 = 25.93%.
- Kazakh grounded recall: 0/3 = 0%.
- 13 expected evidence items were missed.
- 245 internal collision candidates were excluded from eligible answer evidence.

These results are a clear reason to improve retrieval and evidence eligibility before expanding runtime routing or claiming multilingual competence. The cross-lingual bridge is only a hint, not proof of semantic understanding. Unknown-scope, production-unconfirmed, external and manual-review-only records must not become answer evidence.

## Data and safety rules

- Synthetic prompts only; never use real bank/customer/card/device/network data.
- Keep canonical corpus v0.6 unchanged during benchmark construction.
- Gold evidence IDs require source provenance and human relevance review.
- A source record's presence does not automatically make it current, legally authoritative or production-confirmed.
- Separate facts, proposals, implementation status, external research and unknowns.
- Signals, graph links and Cases are not proof of guilt and are not automatic blocking instructions.
- No promise of 100% fraud prevention or guaranteed recovery.
- A new canonical answer must pass near-miss tests and multilingual review before entering the allowlist.

## Implementation sequence

1. Deduplicate and audit the current 50 QA prompts, 8 complex cases and 12 decomposition cases.
2. Map each prompt/subquestion to source records and evidence status; manually review ambiguous or colliding records.
3. Expand to 250 unique prompts according to the coverage matrix and language distribution.
4. Add held-out paraphrases and adversarial near-miss tests not used during tuning.
5. Improve retrieval (normalization, concept aliases, hybrid lexical/dense retrieval only if benchmark evidence justifies it, reranking and evidence filters).
6. Re-run diagnostics and inspect per-language misses before changing production routing.
7. Only then connect any newly validated task classifier or broader canonical allowlist to runtime.
8. Run end-to-end tests against the live answer endpoint after CI and retrieval gates pass.

## Status

Planning baseline only. No new runtime answer routing, retrieval model, embedding dependency, external API, bank integration or production capability is introduced by this document.
