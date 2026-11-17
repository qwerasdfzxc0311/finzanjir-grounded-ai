# FINZANJIR Semantic Understanding and Continuous Learning Evaluation v1

Status: evaluation contract and implementation gate
Branch: feat/semantic-learning-evaluation-v1

## Purpose

Measure whether FINZANJIR understands what the user means, retrieves relevant knowledge without losing useful partial evidence, answers proportionately, and remains useful when hosted providers are unavailable.

This is an evaluation suite, not a claim that the runtime already passes it. Fixture-structure tests only validate coverage and schema. Behavioral tests must call the real local orchestration path and assert semantic outcomes before release.

## Required behavior

1. Parse intent, requested answer shape, domain, language, entities, time sensitivity, and conversation references as separate fields.
2. Preserve the original user text. Normalization is a parallel matching view and must not silently rewrite meaning.
3. Retrieve candidate evidence from the correct knowledge domain. Project facts, author statements/opinions, personal memory, general knowledge, and external research remain separate.
4. Score evidence on relevance, source status, freshness, contradiction, and coverage. A high lexical score alone is not proof of relevance.
5. Answer supported parts even when other parts are unknown. State the exact gap; do not refuse the whole question when useful evidence exists.
6. Do not pad answers with merely adjacent material. Every paragraph must answer a requested sub-question or explain a material limitation.
7. Ask one clarification only when ambiguity materially changes the answer.
8. When a hosted provider fails, switch to local retrieval/rules/composition only where those components can support the answer. Never label extractive fallback as generative reasoning.
9. External research candidates stay quarantined until source, license, content quality, sensitivity, and relevance are reviewed.
10. User corrections and failed evaluations become feedback candidates, not automatic truth or training examples.

## Continuous knowledge lifecycle

Question or public source -> intent and source classification -> bounded retrieval/research -> evidence comparison -> candidate fact with provenance -> contradiction/sensitivity/license checks -> evaluation -> review -> approved knowledge index -> future retrieval -> outcome evaluation.

Every candidate stores source ID, canonical URL or provider reference, retrieval timestamp, content hash, language, license/permission, data class, verification status, and review history. Re-fetching changed content invalidates prior approval.

## Learning layers

- Knowledge growth: add reviewed facts and relations to a versioned knowledge index. This does not change model weights.
- Mechanism improvement: use failure analysis to update normalization, intent, query expansion, ranking, answer planning, or tests. Changes are versioned, tested, and reversible.
- Model training: separate governed pipeline with licensed/non-personal examples, source-grouped train/validation/test splits, native-language review, compute approval, reproducible checkpoints, and rollback. Never train directly on unreviewed web content, private cloud imports, bank/customer data, secrets, or raw user chats.

## Evaluation dimensions

- Intent and requested-answer-shape accuracy
- Language identification and language-consistent response
- Evidence candidate recall and evidence precision
- Partial-evidence usefulness
- Unsupported-claim rate
- Irrelevant-content rate
- False-refusal rate and unsafe-answer rate (tracked separately)
- Follow-up reference resolution and topic-switch handling
- Freshness disclosure for time-sensitive facts
- Provider-outage local capability
- Citation/provenance correctness
- Correction recovery

Critical safety failures block release even if the aggregate score is high. Report results by language and task class; do not hide weak language performance in an overall average.

## Resource and deployment boundaries

- CPU-only deterministic operations are the first target: normalization, conservative Uzbek/Karakalpak/Kazakh/Russian suffix stemming, lexical/concept retrieval, character n-gram typo tolerance, graph traversal, rule checks, scoring, and template composition.
- A small source-backed offline general-knowledge pack currently covers three stable topics (sky colour, Uzbekistan geography, and turtle/tortoise lifespan) in the five project languages. It is not a pretrained model or open-domain generator; unsupported general questions use an available hosted provider or abstain honestly.
- Character n-grams and conservative suffix stemming are typo-/inflection-tolerant lexical matching, not semantic understanding. Do not label them embeddings or semantic reasoning. The BM25 semantic_score remains zero until a genuine semantic model is separately implemented and evaluated.
- Local embeddings and a from-scratch model are optional later experiments, gated by measured benefit and available storage/compute. No pretrained weights are silently introduced.
- Cloudflare D1 may hold compact metadata, audit, source provenance, and encrypted text chunks within verified plan limits. It is not a substitute for object storage or a backup guarantee.
- Worker CPU is for bounded coordination, not model inference, OCR, video processing, or training.
- No paid resources, provider credentials, OAuth scopes, production secrets, existing D1 supervisor tables, or live deployment settings are changed by this evaluation work.

## Release gates

1. Fixture schema and language coverage pass.
2. Native speakers review language and intent labels.
3. Behavioral tests run against the actual local orchestration path, including offline answers in all five languages, source provenance, project/general separation, and honest abstention for unsupported topics.
4. Offline mode test proves no hosted provider request is made.
5. Provider failure test proves correct local fallback or honest limitation.
6. Evidence tests prove no project/general/personal/external source leakage.
7. Before production, compare the deployed API behavior against the same versioned test set and verify rollback.
