# FINZANJIR answer-mode policy (v1)

## Purpose

FINZANJIR must remain an AI assistant, not become a scripted FAQ. Use deterministic answers only for a small, explicitly governed set of high-consequence questions where wording must remain stable. For all other questions, preserve grounded retrieval and model-based explanation, synthesis, and reasoning.

## Three answer modes

1. **Canonical deterministic** — return an approved, versioned answer in the detected language. Use only when the current question clearly matches an approved intent AND the required evidence records are present. Do not trigger from a loose keyword or a prior unrelated turn.
2. **Grounded generative** — retrieve relevant canonical records, filter by evidence status, then let the model explain, connect, compare, and synthesize only what those records support. Distinguish fact, proposal, current implementation, and unknown.
3. **Abstain or clarify** — if evidence is missing, contradictory, stale, or the request is ambiguous, state the evidence gap or ask one focused clarification. Never fill gaps with invented project facts.

Clearly general-knowledge questions remain separate from FINZANJIR project knowledge. External web research must remain labelled as external and must not silently become project fact.

## Initial canonical-answer allowlist

The initial deterministic allowlist is intentionally narrow:

- Author's overall motivation and the project's founding purpose.
- FINZANJIR's short, high-level definition.
- Whether FINZANJIR itself can block a bank card or override a bank decision.
- Whether a suspicious signal proves guilt.
- What a Case is and what it is not.
- What Fraud Graph means at a high level.
- The core false-positive / false-negative fairness principle.
- The C-model definition, only when the approved evidence and language answer are present.
- The sixteen-layer overview, only when the approved evidence and language answer are present.

The allowlist is not permission to use one answer for every question containing the same words. Detailed, contextual, follow-up, status, legal, or implementation questions must use grounded generative mode unless they exactly ask the canonical concept question.

## Grounded-generative question families

These must remain open to evidence-based reasoning rather than one canned paragraph:

- Detailed architecture and component relationships.
- How a workflow or investigation process works.
- Data collection, privacy, retention, access, and sharing.
- Legal basis, regulatory uncertainty, and bank-authority boundaries.
- Pilot design, evaluation, and evidence requirements.
- What is implemented now versus planned or proposed.
- False-positive causes, context, mitigation, and trade-offs.
- Cross-bank signal exchange and privacy-preserving alternatives.
- Incident response, complaint routes, and possible recovery support.
- Comparisons with other systems, countries, or approaches.
- Examples, scenarios, and hypothetical cases.
- Technical troubleshooting, deployment, and roadmap questions.

The list is a routing guide, not a fixed answer bank. The model should select relevant records, explain relationships, and say when the corpus does not contain enough evidence.

## Guardrails

- A deterministic answer requires an exact/semantic intent match plus its required evidence IDs. Evidence absence must cause abstention, not an ungrounded canned answer.
- Do not add a new canonical intent merely because a question was asked often. Require source traceability, owner review, multilingual review, and regression tests.
- Never present a proposal or concept requirement as a deployed capability.
- A risk signal, graph relationship, or Case is not proof of guilt and is not an automatic blocking instruction.
- Do not claim guaranteed fraud prevention, error-free decisions, or guaranteed recovery of funds.
- Keep the user's language. If a vetted canonical translation is unavailable, do not silently return an unrelated language.
- Do not let conversation history make a previous deterministic intent fire for a new, unrelated question.
- Keep general knowledge and external research separate from FINZANJIR's canonical corpus.

## Evaluation before expanding the allowlist

For every new intent, test:
- direct wording, paraphrases, typos, colloquial spelling, and supported languages;
- near-miss questions that mention the same entity but ask something different;
- multi-part and follow-up questions;
- missing or incomplete evidence;
- contradiction between concept documents and implementation status;
- author-name mentions in critique or opinion questions.

Track intent precision, correct routing, answer completeness, citation support, unsupported-claim rate, abstention quality, language match, latency, and cost. Prefer precision over recall for deterministic routing: a missed canned answer can still be answered by grounded generation; a false trigger can replace the user's actual question with the wrong script.

## Current scope

This document governs staged development. It does not claim every listed answer family is already implemented in every language, nor that the router currently supports every proposed family. Runtime changes must be made separately with tests and reviewed evidence.
