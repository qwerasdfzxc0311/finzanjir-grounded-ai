# FINZANJIR Conversation Context Memory v1

## Alignment with the existing FINZANJIR memory architecture

The project archive's “Bilimlar bazasi va xotira arxitekturasi V1” defines six separate layers: (1) authoritative knowledge, (2) candidate/learning knowledge, (3) current conversation, (4) personal memory, (5) historical/archive data, and (6) source/audit metadata. The 16-layer architecture also places knowledge governance and AI reliability in its own layer.

This PR implements only layer 3 (bounded current-conversation context). It does not implement layer 4 (persistent personal memory), and does not merge chat history into authoritative knowledge or candidate knowledge. The author profile records remain separate, source-backed project biography/history: author_0004 (project motivation), author_0005 (biological mother's story from V14), author_0006 (family roles in the first prototype from the historical working document), and author_0007 (project-origin timeline from the historical working document).

## Purpose

Resolve follow-up questions across recent turns without treating earlier assistant text as factual evidence.

## Current implementation scope

- The browser keeps a bounded recent conversation in its existing in-memory aiConversation array.
- Before an AI request, the frontend sends up to 12 previous user/assistant turns.
- The API validates roles and bounds each turn to 1,200 characters.
- The backend uses only clear multilingual anaphora/ellipsis markers to decide whether to inject recent context. Explicit first/second-question references select the matching earlier pair; otherwise the last two user/assistant pairs are used.
- Recent assistant responses are explicitly labeled untrusted context and are used only by answer composition to resolve references; previous assistant text is excluded from intent/retrieval query construction.
- Only previous user questions influence intent and retrieval; prior assistant answers never become search evidence.
- Retrieval and answer generation still require current canonical or author-confirmed evidence.
- The backend does not create a persistent conversation-history database in this version.
- The UI provides a clear-chat control.
- Explicit references to the first or second question select the corresponding earlier user/assistant pair while it remains inside the bounded history window.

## Safety and evidence rules

1. Conversation history is not a knowledge source.
2. An earlier assistant answer cannot become evidence merely because it appears in history.
3. A current user correction supersedes a stale conversational assumption.
4. Ambiguous references should not be guessed; ask one focused clarification.
5. Before external provider calls, a pattern-based guard blocks common card-like 13–19 digit values, email addresses, Uzbek and international phone numbers, passport-like series/number strings, and IBAN-like values. The guard checks the current question and any injected conversation context.
6. This is a best-effort deny-list, not full data-loss prevention: it can miss unfamiliar formats and may conservatively block some ordinary text. Do not submit highly sensitive identifiers or full financial records to the prototype.
7. Context is bounded; the current version does not claim indefinite memory or full cross-session recall.
8. Canonical corpus and author-confirmed biography remain separate from chat history.

## Next iteration

- Add explicit topic/entity stack and rolling summaries for conversations longer than the bounded turn window.
- Add topic-return handling for references such as “go back to my first question”.
- Add ambiguity detection when multiple entities are plausible antecedents.
- Add cross-session memory only after authentication, ownership, encryption, retention, and deletion controls are designed and tested.

## Test coverage

Synthetic tests cover Uzbek Latin/Cyrillic, Russian, English, Karakalpak-style markers, history bounds, independent-question isolation, author-motivation follow-up, author-mother follow-up, API limits, and frontend clear-chat behavior.

 
## 2026-11-15 — Author motivation answer grounding correction

The family card-blocking story must be narrated precisely: the author heard it during a family gathering. The author did not independently investigate the incident and does not know why the card was blocked. The story is not evidence of bank error or wrongdoing. Do not infer the block reason, blame a bank, or claim the author witnessed the event.

The story is a personal impetus, not the sole or complete explanation of every FINZANJIR mechanism. It strengthened a broader design question: how can anti-fraud analysis avoid harming legitimate transfers and innocent citizens when a signal is wrong? Later project mechanisms and requirements emerged through separate research, audits, events and design work; do not claim every module came from this one story.

For author-motivation questions, answer from author_0004 with a deterministic, localized answer before free-form provider generation. Explain the family story and unknown cause, then connect it to the resulting principles: jointly measure false positives and false negatives; treat a signal as neither proof of guilt nor an automatic block instruction; preserve authorized bank/human review; support prompt, fair citizen complaints; inspect missed fraud and mistaken alerts; reduce errors through evidence-based changes and regression tests. State that FINZANJIR is not created to accuse banks or replace their authority. Core principle: make fraud harder without making lawful life harder. Do not promise zero errors.

Regression tests require the exact unknown-cause caveat and verify that the provider is not called for this author-motivation answer. This is a source-grounded response rule, not model fine-tuning or a production deployment.
