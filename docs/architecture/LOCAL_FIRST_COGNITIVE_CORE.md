# FINZANJIR Local-First Cognitive Core

Status: architecture proposal for implementation and review  
Scope: independent conversation and reasoning without Gemini, OpenRouter, or another hosted LLM  
Principle: do not describe the system as human-like or ChatGPT-equivalent until it passes published capability tests.

## 1. Current baseline (audited 2026-11-16)

The current runtime is a grounded knowledge assistant, not yet an independent general-purpose language model.

- `FINZANJIRAI` orchestrates conversation context, intent routing, retrieval, grounding, and answer generation.
- `HybridRetriever` is deterministic lexical BM25-style retrieval. Its own documentation explicitly says semantic embeddings are a future, separately evaluated stage.
- `QueryExpander` supplies local curated rewrites, but the engine also asks `LLMGateway.expand_question()` for model-proposed rewrites.
- `GroundedAnswerGenerator` may call the hosted gateway to compose answers. Its offline fallback is extractive or deterministic; it does not provide broad open-domain generative reasoning.
- `build_conversation_context` accepts at most 12 turns, with bounded text, and uses prior turns as context rather than evidence.
- `generate_general_knowledge` currently depends on the provider path; provider failure can result in an abstention rather than an independent general answer.
- The package dependencies do not currently include a local neural inference runtime or a trained language model.

Therefore, the immediate target is to make the application honestly operable in offline mode, then build and evaluate local understanding/reasoning components. Turning off provider calls alone does not create a general AI.

## 2. Product goal

Build a local-first, multilingual assistant that can:
1. understand the user's wording and intended task, including colloquial and misspelled Uzbek and Karakalpak;
2. resolve references and maintain bounded conversational context;
3. retrieve and connect relevant concepts rather than rely only on exact word overlap;
4. perform transparent, bounded reasoning (classification, comparison, arithmetic, rule-based inference, and evidence synthesis);
5. compose a natural response without requiring a hosted model;
6. distinguish verified FINZANJIR project claims from general knowledge, hypotheses, and unknowns;
7. state uncertainty and ask a useful clarification rather than fabricate.

This is a staged engineering target, not a claim that a small local system can immediately match ChatGPT.

## 3. Two strictly separated knowledge modes

### A. FINZANJIR project mode

- Closed-world by default: project facts must be supported by approved FINZANJIR records and provenance.
- Keep author biography, author opinion, project requirements, implemented code, legal conclusions, and external research as distinct evidence classes.
- A retrieved record is evidence only if its verification/status metadata allows it.
- If evidence is missing, say what is missing. Do not fill gaps with generic internet facts.
- Never turn a risk indicator into guilt, an automatic block, or a bank decision.

### B. General conversation and reasoning mode

- Use a separately curated general-knowledge corpus and locally implemented reasoning tools.
- Keep general knowledge distinct from FINZANJIR source evidence.
- For claims requiring current facts, disclose that offline knowledge may be stale and request an approved update/research path.
- If the local knowledge/reasoning system cannot support an answer, say so clearly.

A project query must never silently fall through to unrelated general knowledge, and general questions must not be rejected solely because the FINZANJIR corpus is closed-domain.

## 4. Proposed local architecture

| Layer | Responsibility | Initial implementation |
|---|---|---|
| Input normalization | Unicode, spelling variants, punctuation, transliteration, script handling | Expand existing normalization with regression corpus |
| Language and intent | Language, speech act, question type, domain, entities | Deterministic local classifier with confidence and unknown class |
| Dialogue state | Follow-up resolution, topic, references, bounded memory | Explicit state object; no implicit permanent storage |
| Semantic representation | Subword/concept features and multilingual mappings | Start with character n-grams + domain lexicon; evaluate local embeddings trained only on approved data |
| Retrieval | Hybrid lexical + concept/semantic retrieval | BM25 plus measured local semantic index; retain provenance filters |
| Knowledge graph | Entities, concepts, relations, time and evidence links | Typed graph with source IDs and contradiction handling |
| Reasoning | Rule inference, arithmetic, comparison, causal hypotheses, constraint checks | Small auditable operators; every conclusion traces to premises |
| Answer planner | Select answer shape, evidence, uncertainty and language | Local response plan, independent of any provider |
| Surface generation | Produce readable text | First: grammar/templates and sentence composition; later: locally trained small model if corpus and compute justify it |
| Safety and privacy | Data minimization, prompt/data boundary, output checks | Local checks, audit events, no third-party transmission by default |
| Evaluation | Capability, factuality, robustness, latency and regression | Versioned multilingual test suite and acceptance gates |

The reasoning layer must not claim to expose hidden chain-of-thought. It should provide concise, checkable reasons and source references.

## 5. No hosted model in the core path

- Introduce an explicit `offline` provider policy that guarantees zero Gemini/OpenRouter requests.
- In offline mode, query expansion and answer planning must use local components only.
- External research, if ever enabled, must be a separately named, explicit user-approved capability; it is not a hidden dependency of conversation.
- A provider timeout must not be described as successful local generative reasoning.
- Telemetry must clearly distinguish `local_rule`, `local_retrieval`, `local_model`, and `hosted_model` generation modes.

## 6. Neural-model strategy and compute reality

The user's requirement is to avoid depending on ready-made pretrained hosted models. The long-term research option is a small model trained from scratch on licensed, reviewed, non-sensitive multilingual data. It must not be trained on real bank/customer records.

Training a ChatGPT-scale model from scratch is not realistic on a Galaxy S22 Ultra or a small personal server. The phone can be used for testing and possibly quantized inference of a sufficiently small model later, but not for training a frontier-scale model. Do not promise parity with ChatGPT. Begin with an auditable neuro-symbolic system; only add a local neural model when dataset size, compute, licenses, and evaluation justify it.

## 7. Milestones and exit criteria

### M0 — Offline contract
- Explicit offline configuration.
- Automated test proves no network/provider method is invoked in offline mode.
- API reports the true generation mode and does not label extractive fallback as a model response.

### M1 — Local language understanding
- Test paraphrases, spelling errors, inflections, mixed scripts and supported languages.
- Correctly distinguish project questions, general questions, follow-ups, requests, comparisons and unknown intent.
- Publish accuracy and confusion cases; do not infer success from a handful of hand-picked prompts.

### M2 — Dialogue continuity
- Resolve references such as “u”, “shuni”, “oldingi fikring” against bounded history.
- Do not let assistant-generated text become evidence.
- Handle topic changes and explicit corrections.

### M3 — Local reasoning
- Add testable arithmetic, comparisons, rule inference and evidence synthesis.
- Each derived conclusion records its premises and method.
- Add contradiction and uncertainty handling.

### M4 — Local semantic retrieval and response composition
- Benchmark against the lexical baseline.
- Improve recall without increasing unsupported answers.
- Compose answers across multiple source records; retain citations and language quality.

### M5 — Optional small model trained from scratch
- Proceed only after data governance, licensing, compute and quality targets are approved.
- Compare with the non-neural local baseline.
- Keep the system useful when the model is unavailable.

## 8. Minimum benchmark before claiming conversational understanding

Build a held-out set with at least 500 examples per supported language over time, including:
- paraphrases and colloquial wording;
- spelling mistakes and transliteration;
- multi-turn follow-ups and topic switches;
- general knowledge vs FINZANJIR project intent;
- questions with insufficient or conflicting evidence;
- reasoning tasks with independently verifiable answers;
- adversarial instructions embedded in retrieved text.

Report intent accuracy, retrieval recall@k, grounded factual precision, abstention quality, answer usefulness, latency and offline success rate separately. A single overall score is not sufficient.

## 9. Safety and governance constraints

- Never train on bank customer data, card numbers, credentials, private messages, or other personal financial records.
- No automatic card blocking, guilt determination, or bank-authority replacement.
- Do not store conversation history permanently without a clear purpose, retention rule and user control.
- Keep source provenance and auditability through retrieval, reasoning and answer generation.
- All changes that affect bank-facing or personal-data workflows require legal and security review before any real-data pilot.

## 10. First implementation sequence

1. Add and test explicit offline provider policy.
2. Ensure the orchestration layer bypasses hosted query expansion in offline mode.
3. Add an offline capability report so the UI says what local functions are actually available.
4. Create a versioned language-understanding benchmark from author-reviewed examples.
5. Implement dialogue-state and local reasoning modules behind stable interfaces.
6. Only then evaluate whether a from-scratch small neural model is justified.

The first implementation must be small, reversible, testable, and must not alter the existing FINZANJIR risk pipeline.
