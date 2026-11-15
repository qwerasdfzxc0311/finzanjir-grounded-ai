# FINZANJIR AI: language understanding and grounded answer quality (v1)

## Purpose

Improve FINZANJIR AI from keyword matching plus concatenated source statements into a multilingual, evidence-grounded assistant that understands the user's intent and explains verified project knowledge in plain language.

This is a staged engineering design, not a claim that the system is already ChatGPT-equivalent or production-ready.

## Canonical knowledge remains authoritative

- The current canonical v0.6 corpus contains 8,804 records and is loaded by the existing knowledge loader.
- The original source statements, record IDs, evidence status and provenance remain unchanged.
- Model-generated query rewrites are search hints only. They cannot add facts or write to the canonical corpus.
- Model-generated answers are constrained to the retrieved, grounded records and return record IDs that are allowlisted against the retrieved context.
- If evidence is absent or unverified, the assistant must abstain or explain the evidence gap.
- External web results must never silently become FINZANJIR project facts.

## Current implementation in this change

1. **Provider gateway:** Gemini is the primary provider when configured; OpenRouter is the fallback. Provider selection is controlled by server environment variables. Keys are never sent to the browser or included in logs.
2. **Question expansion:** The language model can produce a small set of equivalent search queries to help with typos, abbreviations, colloquial Uzbek, synonyms, indirect phrasing and the supported project languages.
3. **Evidence retrieval:** Every expanded query still searches the canonical corpus. Candidate passages are merged, reranked, and filtered by the existing evidence-status rules.
4. **Context:** Grounded context now retains aliases, so the answer model can see canonical wording and known alternate terms together.
5. **Answer composition:** The model is instructed to answer in the user's language, explain what a concept means, why it matters, how it works and where it is used when the evidence supports those details. It must distinguish established facts from proposals and unknowns.
6. **Fallback:** If providers are missing or unavailable, the deterministic fallback presents source statements as separate readable points rather than joining unrelated fragments into one sentence.

## Environment variables

Required only on the API service (never the frontend):

- `GEMINI_API_KEY`
- `OPENROUTER_API_KEY`
- `TAVILY_API_KEY` (only needed for the separate external research endpoint)

Optional:

- `FINZANJIR_LLM_PROVIDER=auto|gemini|openrouter` (default: `auto`; Gemini first, OpenRouter fallback)
- `GEMINI_MODEL=gemini-3.8-flash`
- `OPENROUTER_MODEL=google/gemini-3.8-flash`

The service should be tested with keys present, keys absent, invalid keys, provider timeout, rate limiting and malformed model output. Do not paste API keys into GitHub, Notion, chat messages, source files or browser JavaScript.

## What is still needed for stronger meaning-level understanding

The current change adds model-assisted query expansion, but the retriever still uses lexical matching. It is not yet a full dense-vector semantic search system. The next quality stages should be:

### A. FINZANJIR concept dictionary (curated semantic layer)

Build a derived, versioned glossary without overwriting canonical records. Each concept card should contain:

- canonical concept ID and preferred term;
- plain-language explanation;
- precise definition from the source;
- purpose and what the concept does / does not do;
- where and when it is used;
- known synonyms, spelling variants, abbreviations and colloquial forms;
- Russian, English, Kazakh and Karakalpak variants where verified;
- related concept IDs and relationship type;
- simple examples, clearly marked as illustrative;
- source record IDs, provenance, evidence status and review state.

The dictionary must be generated from the canonical corpus and its knowledge graph, then reviewed. A model may suggest definitions or synonyms, but it must not silently approve them.

### B. Multilingual semantic retrieval

Evaluate a multilingual embedding model against the actual FINZANJIR benchmark. Candidate approaches include Gemini Embedding 2 and BGE-M3. Keep lexical retrieval because exact names, IDs, legal terms and short labels often need exact matching.

Recommended pipeline:

1. normalize spelling and script without changing meaning;
2. expand the query with aliases and equivalent formulations;
3. run lexical and dense-vector retrieval;
4. merge candidates using Reciprocal Rank Fusion (RRF);
5. rerank the combined candidate set;
6. filter by evidence status and relevance;
7. send only the strongest grounded passages to answer generation.

Do not choose a model from marketing claims alone. Measure recall, citation precision, answer support, latency and cost on the FINZANJIR test set.

### C. Detailed answer quality

Answers should be driven by the question, not a fixed word count. For a definition question, explain meaning, purpose and a simple example. For a process question, explain the sequence and roles. For a comparison, explain the important differences. For a legal or banking question, distinguish what the corpus establishes from what still requires legal confirmation.

Do not pad answers. A longer answer is only better when it adds relevant, supported explanation.

### D. Tavily and external research isolation

Tavily is a web-search source, not a language model and not a project knowledge authority. This change exposes it through a separate `POST /api/research/search` endpoint for general/current research. It returns source URLs and snippets labelled as external web research; it does not alter the FINZANJIR AI answer endpoint. Common personal/payment identifiers are rejected before a Tavily request. Do not merge Tavily snippets into the canonical FINZANJIR corpus automatically. A human-reviewed ingestion step is required before any external source can become project knowledge.

## Evaluation plan

Build a versioned benchmark with at least 150–300 prompts covering:

- Uzbek Latin and Cyrillic, Russian, English, Kazakh and Karakalpak;
- misspellings, missing apostrophes, phonetic spelling and colloquial wording;
- synonyms and indirect questions;
- short, ambiguous and multi-part questions;
- definitions, purpose, process, examples, comparisons and limitations;
- questions whose answer is absent from the corpus;
- adversarial prompts that try to make the model invent capabilities or override evidence;
- author-name mentions that must not be mistaken for evidence of agreement or endorsement.

Measure separately:

- retrieval Recall@5 / Recall@10;
- answer relevance and completeness;
- citation precision and whether cited records actually support the answer;
- unsupported-claim rate;
- correct abstention rate;
- language match and plain-language comprehension;
- latency, token use and cost per answer.

A small synthetic test set is not proof of real-world accuracy. Human review remains necessary for the benchmark and for changes to the canonical knowledge.

## External technical references

- Microsoft Learn, RAG information retrieval: hybrid search, Reciprocal Rank Fusion, reranking and evaluation: https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/rag/rag-information-retrieval
- BAAI BGE-M3 model card: multilingual dense/sparse retrieval and recommendation to combine hybrid retrieval with reranking: https://huggingface.co/BAAI/bge-m3
- Google Gemini model catalogue: current generation and embedding model availability: https://ai.google.dev/gemini-api/docs/models
- Gemini structured outputs: JSON schema output and the need for application-side semantic validation: https://ai.google.dev/gemini-api/docs/structured-output
- OpenRouter structured outputs and provider-specific support: https://openrouter.ai/docs/guides/features/structured-outputs

## Safety and scope

- No bank, card, customer, device or network data is sent to an AI provider.
- Do not use real customer data in tests.
- Cross-bank exchange remains disabled.
- The model cannot change risk scores, open cases, block accounts or make bank decisions.
- The AI answer endpoint is informational and grounded in the project corpus only.
- This change does not fine-tune a new foundation model. It uses existing models with retrieval, controlled prompts and evidence validation.


## Author-purpose answers: source hierarchy and safety

Questions such as "Muallif nima uchun FINZANJIRni yaratgan?", "FINZANJIRning asosiy maqsadi nima?", "Why was FINZANJIR created?" and close semantic variants use a deterministic, source-grounded answer rather than free-form provider generation.

The answer composes three separate author-profile records:
- `author_0004`: the narrower project-origin context, including the family anecdote. The author did not independently investigate the reported card block and does not know its cause; it is not evidence of bank error or wrongdoing.
- `author_0008`: the broader purpose and future-facing perspective from V14 chapter 15 (sections 15.1–15.10 and 15.12, including harm reduction, non-stigmatization, convenience/trust, continuous development, international learning, and financial resources as a means rather than an end).
- `author_0009`: the human motivation described in V14 section 15.11.1, without disclosing unrelated private family details.

The router loads the complete author profile for clear purpose questions. It does not trigger on a bare author-name match or a critique/opinion question. If any required evidence record is missing, the answer abstains rather than presenting the narrow anecdote as the complete motivation.

The response must distinguish the author's stated intention from implemented product capability. It must not imply that every concept feature is already deployed, that banks are at fault, or that FINZANJIR can guarantee zero fraud or zero errors. A signal is not proof of guilt and is not an automatic blocking instruction; bank authority and human review remain.
