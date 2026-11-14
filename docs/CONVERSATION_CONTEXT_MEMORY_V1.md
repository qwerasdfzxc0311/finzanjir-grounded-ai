# FINZANJIR Conversation Context Memory v1

## Purpose

Resolve follow-up questions across recent turns without treating earlier assistant text as factual evidence.

## Current implementation scope

- The browser keeps a bounded recent conversation in its existing in-memory aiConversation array.
- Before an AI request, the frontend sends up to 12 previous user/assistant turns.
- The API validates roles and bounds each turn to 1,200 characters.
- The backend uses only clear multilingual anaphora/ellipsis markers to decide whether to inject recent context.
- Recent assistant responses are explicitly labeled untrusted context and are used only to resolve references and topic continuity.
- Retrieval and answer generation still require current canonical or author-confirmed evidence.
- The backend does not create a persistent conversation-history database in this version.
- The UI provides a clear-chat control.

## Safety and evidence rules

1. Conversation history is not a knowledge source.
2. An earlier assistant answer cannot become evidence merely because it appears in history.
3. A current user correction supersedes a stale conversational assumption.
4. Ambiguous references should not be guessed; ask one focused clarification.
5. Sensitive payment/identity strings must not be sent to external model providers. Provider calls evaluate the current question together with conversation context.
6. Context is bounded; the current version does not claim indefinite memory or full cross-session recall.
7. Canonical corpus and author-confirmed biography remain separate from chat history.

## Next iteration

- Add explicit topic/entity stack and rolling summaries for conversations longer than the bounded turn window.
- Add topic-return handling for references such as “go back to my first question”.
- Add ambiguity detection when multiple entities are plausible antecedents.
- Add cross-session memory only after authentication, ownership, encryption, retention, and deletion controls are designed and tested.

## Test coverage

Synthetic tests cover Uzbek Latin/Cyrillic, Russian, English, Karakalpak-style markers, history bounds, independent-question isolation, author-motivation follow-up, author-mother follow-up, API limits, and frontend clear-chat behavior.
