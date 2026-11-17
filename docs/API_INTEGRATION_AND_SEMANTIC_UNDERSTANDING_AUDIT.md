# FINZANJIR API integration and semantic-understanding gap audit

Status: engineering audit / implementation gate. This document does not enable any provider, change production configuration, or promote private imports into canonical project knowledge.

## Confirmed current state

### Runtime and canonical project knowledge
- `/api/ai/answer` calls the shared `FINZANJIRAI` orchestration engine.
- The API's `knowledge_index()` is built from `SystemFlow.demo_knowledge_index()`. Despite the historical method name, this loader reads and validates `data/canonical_knowledge_v0.6.json`, then adds the separately governed author profile and project-principles records.
- Project and author records are kept in separate retrieval routes/domains. This separation must be preserved.
- Retrieval is currently BM25/lexical plus alias-aware reranking, script variants, cross-lingual term hints, and optional model-proposed query expansion. The hybrid retriever explicitly documents that it is lexical; semantic embeddings are not yet implemented/evaluated as a separate stage.
- Do not replace the current evidence filters with unconstrained semantic similarity. A semantic layer may improve candidate recall only; source-domain filters, provenance, reranking, and abstention remain authoritative.

### Google personal-cloud integration
- Google OAuth/API routes are registered in FastAPI.
- Implemented routes include owner login/session, account list/disconnect, Drive listing and selected-file import, Gmail listing and selected-message import, Google Photos Picker and selected-media import, personal-memory source listing/reading, and diagnostics.
- Google tokens and imported content are encrypted server-side. OAuth state is one-time; account count is capped at 100.
- Imported Drive/Gmail text and media are quarantined and owner-scoped. The import response explicitly says the material is not automatically added to the canonical knowledge base.
- The personal-memory store exposes list/read/search/audit primitives, but no owner approval/promotion workflow was found in the inspected store API. Its search currently searches quarantined text only.
- The API answer path does not query the personal-memory store. This is intentional isolation today, but means owner-selected and reviewed private material is not yet usable as a distinct personal-memory context.

### Dropbox and Microsoft OneDrive
- `cloud_sources.py` only publishes a safe provider capability/readiness registry and approved read-only scopes.
- It explicitly states it is not an OAuth implementation. No Dropbox or OneDrive authentication, token vault, import, extraction, revocation, or memory API was found in that module.
- Do not show these providers as connected or enable their connect buttons until their full security lifecycle exists.

### Persistence and Cloudflare
- The Google integration uses two SQLite stores: Google OAuth/account/session state and personal-memory data.
- The runtime deployment audit found the Render API on the free plan without a persistent disk. A local SQLite path on an ephemeral filesystem is not durable across redeploy/restart.
- The existing Cloudflare Worker/D1 resource is a supervisor/checkpoint coordinator, not the Google memory API. It has no authenticated D1 data API for these stores.
- Therefore, do not turn on Google OAuth/import in production until durable persistence is implemented and verified. Do not modify the existing supervisor tables or behavior as part of a memory migration.

## Required implementation sequence

### Phase A — establish durable persistence without changing production
1. Put the exact currently deployed Worker source under version control and compare it against the deployed script before editing.
2. Preserve the existing supervisor behavior and schema. Add new application tables under a separate namespace through versioned migrations.
3. Implement a narrow Worker API, not arbitrary SQL. Authenticate Render-to-Worker requests with HMAC over method, path, timestamp, nonce, and body digest; enforce a short replay window, one-time nonce use, constant-time signature comparison, strict action allowlists, rate limits, and audit events.
4. Keep encryption/decryption at the trusted application boundary. Store only ciphertext for OAuth tokens, private source text, and sensitive metadata. Never log credentials or plaintext content.
5. Test atomic one-time OAuth-state consumption, per-owner/per-account isolation, revocation, source deletion, backup/restore, replay rejection, key rotation strategy, and failure-closed behavior.
6. Do not create paid storage, enable R2, add a Render disk, or alter production secrets/resources without explicit authorization. If the existing free-tier limits cannot meet the required retention/recovery guarantees, disclose that limitation instead of pretending durability.

### Phase B — finish the private-memory lifecycle
1. Add owner-visible review states: quarantined, approved-for-personal-memory, rejected, revoked/deleted.
2. Approval must be explicit, attributable, timestamped, and reversible. A changed source hash returns the item to quarantine.
3. Build a separate personal-memory retrieval context, scoped to the authenticated owner and selected connected accounts.
4. Add personal-memory citations/provenance that identify provider, account alias, source name, import time, content hash, and source ID without exposing tokens or unnecessary private metadata.
5. Personal memory must never be merged into FINZANJIR's canonical project knowledge, training corpus, or another user's retrieval context automatically.
6. Large photos/videos/audio binaries must not be stored in D1. Keep only approved metadata and extracted text/transcripts there unless a separately approved durable object store is configured.

### Phase C — provider integrations
1. Complete Dropbox OAuth/PKCE, token encryption, refresh, revoke, per-account isolation, audit, and selected-file import.
2. Complete Microsoft identity/OneDrive OAuth/PKCE, least-privilege read-only scopes, token encryption, refresh, revoke, audit, and selected-file import.
3. Reuse the same provider-neutral source model and extraction limits; do not create parallel, inconsistent memory stores.
4. Provider readiness must reflect real end-to-end configuration and health, not merely the presence of a client ID.

### Phase D — stronger meaning understanding
1. Establish a multilingual evaluation set before changing ranking. Include Uzbek Latin/Cyrillic, Karakalpak Latin/Cyrillic, Kazakh, Russian, and English.
2. Include paraphrases, spelling/no-diacritic variants, inflections, short follow-ups, topic switches, comparison, status-vs-plan, author fact-vs-opinion, and ambiguous questions.
3. Score intent accuracy, evidence recall@k, evidence precision, answer support rate, citation correctness, abstention quality, language fidelity, and contradiction rate.
4. Add query decomposition and concept-level retrieval hints as candidate generation only. Preserve the original query as the primary ranking signal.
5. Consider multilingual embeddings only after a local/offline-compatible model is selected and evaluated. No ready pretrained model weights are to be silently adopted; model licensing, training provenance, compute needs, and data rights must be reviewed.
6. Answer generation must separate: confirmed source facts, author-confirmed personal statements, project principles/requirements, implementation status, external research, and inference/opinion.
7. When asked for critique (for example, whether the author overpraises the project), do not answer from the author's name or biography match. State what sources establish, what is the author's viewpoint, and what can/cannot be independently evaluated.
8. Follow-up context helps resolve references but is never evidence. Prior assistant responses remain untrusted context.

## Release gates

- No production deployment until tests, migration rehearsal, backup/restore, and security review pass.
- No automatic promotion from private memory into canonical FINZANJIR knowledge.
- No automatic bank action, blocking, or authoritative decision from AI output.
- No secrets in GitHub, APK, frontend bundles, logs, or chat.
- No change to established FINZANJIR mission/architecture decisions without explicit owner approval.
