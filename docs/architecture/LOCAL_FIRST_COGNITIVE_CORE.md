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

## 11. Cloud-assisted capability without cloud dependence

The user has no dedicated cloud infrastructure today. FINZANJIR may therefore connect to 4–5 independent cloud services as optional, replaceable workers, while its core remains local-first.

### Provider-neutral worker roles

Do not send every prompt to every provider. Route only the task that needs help:
- language specialist: translation, script conversion, and low-resource language review;
- research worker: retrieval from approved public sources, with URLs and dates;
- reasoning critic: independently check a proposed conclusion or calculation;
- response editor: improve clarity and grammar without adding facts;
- optional specialist model: a narrowly scoped task selected by benchmark results.

Potential providers are not fixed in this architecture. Each adapter must be selected after checking current terms, supported regions, data retention, pricing, latency, and security. Provider names and model IDs belong in deployment configuration, not business logic.

### Orchestration policy

- Local normalization, intent, conversation state, project retrieval, and safety checks run first.
- A task router may select zero, one, or at most two workers by default. Multi-provider fan-out is reserved for explicitly approved high-value tasks.
- Each worker receives only the minimum task-specific text, never the entire conversation or project corpus by default.
- Independent answers are compared against source evidence. Majority vote is not proof: correlated models can repeat the same error.
- If providers disagree, return the disagreement and uncertainty; do not average unsupported claims into a confident answer.
- Provider timeout, quota exhaustion, or outage must degrade gracefully to local functions.
- Every response records which mode actually ran: local-only, cloud-assisted, or unavailable. Never label cloud output as an independent local-model answer.

### Privacy and legal gates

- Default policy is no third-party transmission.
- Before any cloud call, run sensitive-data detection and purpose/consent checks. If the request contains bank/customer identifiers, credentials, personal financial data, or other protected information, block cloud routing unless a separately approved legal basis and technical control exist.
- The current identifier deny-list is not sufficient DLP. A real deployment needs stronger detection, redaction, allow-listed data classes, provider contracts, retention review, and auditable controls.
- Never send real bank/customer data to public model endpoints for training or inference.
- Cloud plugins/connectors are tool integrations, not a substitute for language training. They may provide controlled search, translation, file access, or compute only through explicit adapters and permissions.

## 12. Language learning and knowledge growth

- Keep separate datasets for language examples, general knowledge, FINZANJIR project evidence, author-provided material, and external research.
- Every knowledge item needs source, date, language, license/permission, verification status, and a revision trail.
- User corrections can become candidate language examples only after review; do not silently convert a single correction into a global rule.
- Build language packs for Uzbek Latin/Cyrillic, Karakalpak Latin/Cyrillic, Kazakh, Russian, and English. Track dialect and transliteration variants without erasing the original input.
- Plugins may import approved dictionaries, corpora, or terminology lists. They must preserve license metadata and cannot silently overwrite verified project facts.
- Train/evaluate on held-out examples. Separate learning data from test data to avoid inflated scores.
- For a from-scratch model, require a documented corpus inventory, license review, deduplication, privacy filtering, tokenizer evaluation, training plan, compute budget, and benchmark before training begins.

## 13. Practical deployment without owned cloud

Use a portable deployment profile:
1. local development and offline tests on the user's device or a trusted workstation;
2. one small hosted API/control plane for the application when online service is needed;
3. optional independent model/research workers behind provider adapters;
4. no mandatory single-provider dependency and no requirement to keep all workers running;
5. configuration and secrets managed per environment, never committed to Git.

Do not distribute API keys inside the Android APK. The client must call the FINZANJIR backend; the backend applies policy and keeps secrets server-side. If no cloud is available, local-only mode remains explicit and honest.

## 14. Expanded five-track delivery plan

All five tracks are developed in parallel only where interfaces are independent; integration is staged behind tests.

| Track | First deliverable | Acceptance gate |
|---|---|---|
| Language understanding | Normalization, spelling/alias packs, intent benchmark | Held-out paraphrase and typo tests across scripts |
| Conversation memory | Explicit dialogue state and reference-resolution tests | Topic shifts and follow-ups do not contaminate evidence |
| Local reasoning | Safe calculator, typed facts, auditable inference rules | Every derived result has traceable premises; unsafe expressions rejected |
| Independent response | Local answer planning and sentence composition | Correctly distinguishes grounded extractive, rule-composed, and model-generated output |
| Own neural model | Dataset governance and feasibility study first | No training until corpus, rights, compute and baseline results are approved |

Cloud worker adapters, language packs, and knowledge ingestion are supporting capabilities, not a sixth hosted-model dependency.


## Verification gate

The consolidated local-first branch must pass the full repository test suite before merge. This document describes design intent; it is not evidence that a trained neural model or production deployment exists.
