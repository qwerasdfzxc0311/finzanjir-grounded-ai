# FINZANJIR multilingual evaluation corpus expansion — consolidated status

## Corpus size

Five synthetic benchmark batches have now been prepared on the draft PR branch:

| Batch | Prompts | Focus |
|---|---:|---|
| 1 | 60 | Project identity, architecture, privacy, fairness, status, AI grounding, author-name near-miss, general knowledge |
| 2 | 60 | Fraud patterns, legal uncertainty, complaints/recovery, pilot evaluation, score-as-guilt adversarial cases |
| 3 | 60 | High-priority canonical-intent routing versus grounded answers for other key questions |
| 4 | 60 | Multi-part questions and adversarial legal, status, false-positive, comparison, recovery, and author-credential traps |
| 5 | 36 | History contamination, document prompt injection, contradictory sources, ambiguity, language quality, author-critique handling |
| **Total** | **276** | **Six language/script groups** |

Batch 1–4 contain 10 prompts per language/script each: Uzbek Latin, Uzbek Cyrillic, Russian, English, Kazakh, and Karakalpak. Batch 5 contains 6 per language/script. The corpus has 46 prompts per group overall (276 / 6).

## Answer-mode balance

Batch 3 explicitly separates:
- 36 tests for six existing canonical answer families: project overview, author motivation, bank authority, signal-not-guilt, Case definition, and Fraud Graph.
- 24 grounded-generation tests for C-model, sixteen layers, Risk Score, and Cross-Match.

Across all 276 prompts, the answer mode is not a blanket canned-answer instruction. Most prompts remain grounded-generative; clarification is expected for genuinely ambiguous cases. The canonical test questions must trigger only when intent and required source evidence match.

## Important canonical-answer requirement

The previously approved full Uzbek author-motivation answer must remain intact and be emitted for a direct author-motivation question when its evidence requirements are met. It must not be replaced by a short generic response or a free-form model guess.

Also keep project mission distinct from the author's personal motivation. A question asking what FINZANJIR does is not always asking why its author created it.

## Review and validation status

- Every new prompt is synthetic; no customer or bank data is included.
- No new canned answers or canonical knowledge facts are introduced by these batches.
- Evidence IDs remain empty pending exact source-record and provenance review.
- Kazakh and Karakalpak wording requires native-speaker review.
- Cross-batch exact duplicate check: 276 new prompts are unique within the new corpus. One exact overlap with the pre-existing QA/decomposition fixtures is intentional: the misspelled turtle-lifespan query is retained as a normalization regression test.
- Existing baseline decomposition artifact is a small diagnostic only; its recall rates are not production capability claims.
- CI must complete on the final branch head before the PR can be considered validated.

## Next work after this fixture

1. Review native-language quality for Kazakh and Karakalpak, and check Uzbek Cyrillic/Latin equivalence.
2. Map every expected evidence requirement to exact canonical source IDs, provenance, and source status. Do not fill IDs based on lexical matches alone.
3. Add evidence-level diagnostic traces so missing candidate retrieval can be separated from grounding-gate rejection.
4. Expand the live endpoint benchmark and run the 276 prompts against the actual deployed endpoint in controlled batches, with secrets protected and no sensitive data.
5. Manually score semantic correctness, answer completeness, source support, language quality, near-miss precision, abstention, and hallucination risk.
6. Only then decide whether any runtime retrieval or intent-router change is warranted.

## Change boundary

This PR is a benchmark and documentation expansion only. It does not modify runtime routing, answer generation, canonical corpus, live API, bank integration, or Render deployment. A later runtime PR must have its own focused tests and deployment verification.
