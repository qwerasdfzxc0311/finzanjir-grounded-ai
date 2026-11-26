# FINZANJIR multilingual evaluation corpus expansion — consolidated status

## Corpus size

Six synthetic benchmark batches have now been prepared on the draft PR branch:

| Batch | Prompts | Focus |
|---|---:|---|
| 1 | 60 | Project identity, architecture, privacy, fairness, status, AI grounding, author-name near-miss, general knowledge |
| 2 | 60 | Fraud patterns, legal uncertainty, complaints/recovery, pilot evaluation, score-as-guilt adversarial cases |
| 3 | 60 | High-priority canonical-intent routing versus grounded answers for other key questions |
| 4 | 60 | Multi-part questions and adversarial legal, status, false-positive, comparison, recovery, and author-credential traps |
| 5 | 36 | History contamination, document prompt injection, contradictory sources, ambiguity, language quality, author-critique handling |
| 6 | 24 | Expert-facing legal operability and international analogue questions; candidate prepared-answer wording remains review-only |
| **Total** | **300** | **Six language/script groups** |

Batch 1–4 contain 10 prompts per language/script each: Uzbek Latin, Uzbek Cyrillic, Russian, English, Kazakh, and Karakalpak. Batch 5 contains 6 per language/script. The first five batches have 46 prompts per group (276 / 6). Batch 6 adds four prompts per group, bringing the expanded corpus to 50 prompts per group (300 / 6).

## Answer-mode balance

Batch 3 explicitly separates:
- 36 tests for six existing canonical answer families: project overview, author motivation, bank authority, signal-not-guilt, Case definition, and Fraud Graph.
- 24 grounded-generation tests for C-model, sixteen layers, Risk Score, and Cross-Match.

Across all 300 prompts, the answer mode is not a blanket canned-answer instruction. Most prompts remain grounded-generative; clarification is expected for genuinely ambiguous cases. The canonical test questions must trigger only when intent and required source evidence match.

## Important canonical-answer requirement

The previously approved full Uzbek author-motivation answer must remain intact and be emitted for a direct author-motivation question when its evidence requirements are met. It must not be replaced by a short generic response or a free-form model guess.

Also keep project mission distinct from the author's personal motivation. A question asking what FINZANJIR does is not always asking why its author created it.

## Expert-facing answer candidates (batch 6)

Batch 6 adds two high-priority question families: (1) whether FINZANJIR is legal / can lawfully operate in Uzbekistan, and (2) whether similar initiatives exist internationally and whether FINZANJIR is copied or adapted. Candidate Uzbek answers are documented in `docs/CANDIDATE_PREPARED_ANSWERS_LEGALITY_AND_INTERNATIONAL_COMPARISON_V1.md`. They are deliberately **not** marked as runtime canonical answers: legality depends on current law, actual data flows, actors, permissions, and regulator/bank review; international comparisons require verified source mapping and clear limits. The batch contains 24 synthetic prompts, four per language/script.

The legal draft distinguishes the author's intention and design requirements from legal authorization or completed compliance. It requires data minimization, purpose limitation, lawful basis, limited retention, access controls, audit, and legally permitted minimal signals, while warning that pseudonymization or a signal label does not automatically remove bank-secrecy or personal-data obligations.

The international draft cites FATF 2026 examples and carefully distinguishes public-private partnerships, fraud-account information sharing, and anti-scam operations. It does not claim FINZANJIR is unique, identical to another system, or a copy. Claims that an initiative closed because of funding must be individually sourced before use.

## Review and validation status

- Every new prompt is synthetic; no customer or bank data is included.
- No new canned answers or canonical knowledge facts are introduced by these batches.
- Evidence IDs remain empty pending exact source-record and provenance review.
- Kazakh and Karakalpak wording requires native-speaker review.
- Exact duplicate check: all 276 new prompts are unique within the new corpus. Two exact overlaps with pre-existing fixtures are intentional regression coverage: (1) the misspelled Uzbek turtle-lifespan query tests typo normalization and general-knowledge routing; (2) the Russian author-motivation question repeats an existing live QA prompt to verify the approved canonical answer remains stable. No unintended exact duplicates were found.
- Existing baseline decomposition artifact is a small diagnostic only; its recall rates are not production capability claims.
- CI must complete on the final branch head before the PR can be considered validated.

## Next work after this fixture

1. Review native-language quality for Kazakh and Karakalpak, and check Uzbek Cyrillic/Latin equivalence. Batch 6 translations are prompts for routing tests, not approved localized gold answers.
2. Map every expected evidence requirement to exact canonical source IDs, provenance, and source status. Do not fill IDs based on lexical matches alone.
3. Add evidence-level diagnostic traces so missing candidate retrieval can be separated from grounding-gate rejection.
4. Expand the live endpoint benchmark and run the 276 prompts against the actual deployed endpoint in controlled batches, with secrets protected and no sensitive data.
5. Manually score semantic correctness, answer completeness, source support, language quality, near-miss precision, abstention, and hallucination risk.
6. Obtain qualified Uzbek legal/compliance review of the legality draft and verify every legal statement against current official law and actual proposed data flows.
7. Complete primary-source comparison of international examples, including governance, legal basis, scope, funding, outcomes, and any documented closure reasons.
8. Only then decide whether any runtime retrieval or intent-router change is warranted.

## Change boundary

This PR is a benchmark and documentation expansion only. It does not modify runtime routing, answer generation, canonical corpus, live API, bank integration, or Render deployment. A later runtime PR must have its own focused tests and deployment verification.
