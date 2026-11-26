# FINZANJIR canonical answer register and expansion governance

## Purpose

FINZANJIR should answer a small set of important, stable questions with complete, reviewed answers prepared in advance. This protects users from a model producing an incomplete, misleading, or inconsistent answer on high-consequence topics. It does not turn the assistant into a static FAQ: all other questions continue through evidence retrieval and generative explanation.

A prepared answer is not a shortcut around evidence. It must be linked to verified source records, versioned, localized, and activated only when the current question's intent matches. A keyword mention or previous conversation turn is never enough.

## Existing runtime answer families found in source review

A read-only inspection of `src/finzanjir_ai/answer/generator.py` found localized answer dictionaries and/or dedicated response paths for:

| Intent | Existing answer path | Required boundary |
|---|---|---|
| FINZANJIR overview | `PROJECT_OVERVIEW_ANSWERS` | Describe purpose without implying every planned capability is deployed. |
| Author motivation | `AUTHOR_MOTIVATION_ANSWERS` | Use the complete, previously approved explanation and its three required author evidence records. |
| Bank authority | `BANK_AUTHORITY_ANSWERS` | FINZANJIR does not itself block cards or override a bank. |
| Signal and guilt | `SIGNAL_GUILT_ANSWERS` | A signal is not proof of guilt or an automatic block instruction. |
| Case purpose | `CASE_PURPOSE_ANSWERS` | A Case is a structured review record, not a verdict. |
| Fraud Graph | `FRAUD_GRAPH_ANSWERS` | A graph link is context for review, not proof of guilt. |

The source code also contains specialized C-model and sixteen-layer query handling. Those remain conditional on the correct evidence and language answer being present; this document does not claim their full localized answer quality has been independently verified.

The existing Uzbek author-motivation response is the long, user-approved answer ending with the principle: «Firibgarlikni qiyinlashtirish, qonuniy hayotni esa qiyinlashtirmaslik». Preserve its substance and required evidence mapping. Do not replace it with a shorter generic statement or a model-generated paraphrase when the direct motivation intent is matched.

## Additional high-priority answer candidates

These are candidates for a future reviewed answer registry, not yet approved canned answers:

1. **Project mission vs. author's personal motivation.** Keep these as separate intents. "FINZANJIR nima uchun yaratilgan?" may ask about the project's purpose; "Muallif nima sababdan yaratgan?" asks about the author's motivation. Do not silently substitute one for the other.
2. **Risk Score meaning and limits.** Explain only what the current canonical sources support; never imply that a score proves guilt or automatically authorizes blocking.
3. **Cross-Match definition and role.** Define the documented concept, not unverified production capability.
4. **False-positive and false-negative fairness.** Explain why both error types matter and why lawful citizens must not be unnecessarily burdened.
5. **Implemented prototype vs. planned capability.** This is a high-value status answer, but it must be checked against the current deployed commit before each release.
6. **Data privacy, minimization, and bank secrecy.** Do not state that an exchange is legally permitted unless the applicable legal source and conditions are verified.
7. **Human review and bank decision authority.** Clarify who may assess a signal and who has legal authority to decide.
8. **Citizen complaint and correction route.** Distinguish documented project design from currently available operational service.
9. **Pilot readiness.** Separate legal permission, bank approval, technical readiness, security assessment, and measured pilot outcomes.
10. **Fraud-chain analysis and citizen protection.** Describe supported mechanisms without promising prevention or recovery.

These topics are not all equally suitable for deterministic answers. Stable definitions and safety boundaries are stronger candidates. Current legal permissions, production status, pilot readiness, and recovery outcomes change over time and should normally remain evidence-grounded, date-aware answers rather than frozen scripts.

## Approval checklist for each new prepared answer

Before a new canonical answer is enabled:

- identify the exact user intent and list near-miss questions that must not trigger it;
- link every material statement to exact canonical source record IDs and provenance;
- verify the source status (fact, proposal, requirement, prototype, deployed, or unknown);
- have the Uzbek wording reviewed and obtain native-speaker review for Russian, English, Kazakh, and Karakalpak translations;
- preserve one meaning across languages and do not silently fall back to another language;
- test typos, colloquial forms, paraphrases, multi-part questions, follow-ups, and critical near-misses;
- test missing or conflicting evidence and require abstention/clarification rather than unsupported output;
- record answer version, source corpus version, reviewer, and last verification date;
- keep a regression test for the exact approved wording and for false-trigger cases.

## Routing rule

- Direct question matching an approved stable intent + required evidence present: return its prepared answer.
- Detailed follow-up, comparison, scenario, or question that asks for more than the prepared answer: use grounded generative mode and cite/refer to supporting project evidence.
- Current, legal, implementation, or operational question: retrieve current verified evidence; do not rely on a stale static answer.
- Incomplete or contradictory evidence: answer supported parts and state the gap.
- General-knowledge question: keep it outside FINZANJIR project facts.

## Scope of this change

This register is a design and benchmark artifact only. It does not add or alter runtime answer handlers, canonical knowledge records, legal claims, bank integrations, API behavior, or deployment. Runtime changes must be proposed separately, reviewed against exact evidence, tested, and deployed only after approval.
