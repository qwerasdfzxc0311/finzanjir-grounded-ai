# FINZANJIR secure cloud connectors

## Goal

Allow FINZANJIR to discover and read approved project knowledge in user-authorized cloud stores while keeping each user's files private, traceable, and separate from FINZANJIR's authoritative project corpus and training datasets.

## Current implementation status

This change adds a provider policy registry and a read-only readiness endpoint. It does **not** connect a cloud account, perform OAuth, read files, store tokens, or run cloud synchronization. The API reports connections as disabled until the security controls below are implemented. This is deliberate: the current prototype has no authenticated per-user identity/session boundary, so enabling account linking now could expose one user's connected files to another visitor.

Supported provider policy descriptions:
- Dropbox: metadata and file-content read scopes only.
- Microsoft OneDrive: Files.Read and User.Read only.
- Google Drive: drive.file (app-created or explicitly selected files), not broad full-drive access.

No write, delete, move, upload, public-link, or share permission is included.

## Required connection architecture

1. **User identity first.** Add a real sign-in/session layer with secure, HttpOnly, SameSite cookies, CSRF protection, session rotation, logout, and per-user authorization. A public static website must never hold provider client secrets or refresh tokens.
2. **OAuth 2.1 Authorization Code + PKCE.** Use exact registered HTTPS redirect URIs, cryptographically random single-use state, PKCE S256, issuer/audience validation where supported, nonce where applicable, strict callback validation, and short-lived authorization codes. Never accept arbitrary callback URLs or provider-supplied redirect targets.
3. **Encrypted token vault.** Encrypt access and refresh tokens at rest with a managed key (KMS or equivalent), separate from the database. Never log tokens, return them to the browser, place them in URLs, or store them in localStorage. Support refresh-token rotation, revocation, expiry, and disconnect.
4. **Least privilege.** Request only the listed read scopes. Start with user-selected folders/files where the provider supports it. Do not request write or public-sharing scopes. A later write feature must be a separate reviewed permission and explicit user action.
5. **Per-user isolation.** Every connection, source, cache record, job, and query must be bound to an authenticated user and checked server-side. No global shared token or cross-user search.
6. **Read-only ingestion.** Import only user-selected content within file-count, size, MIME-type, and rate limits. Treat every cloud document as untrusted input. Prevent prompt injection from document contents. Preserve provider ID, owner/account ID, path/name, version/etag, modified time, content hash, source URL, import time, and granted scopes.
7. **Quarantine and review.** Cloud content remains a candidate source. It must not overwrite FINZANJIR's authoritative documents, enter the training corpus, or be promoted automatically. Require source ownership/permission checks, licence and sensitive-data review, and an explicit approval event.
8. **Audit and user controls.** Show connected account, provider, exact scopes, selected folders, last sync, imported files, failures, and audit history. Provide pause, disconnect, token revocation, and deletion of FINZANJIR's cached copy. Disconnect must stop scheduled jobs and revoke tokens where supported.
9. **Safe background sync.** Use a host scheduler with per-user and per-provider quotas, bounded pagination and byte budgets, backoff, rate-limit handling, and no background sync until the user explicitly enables it. No hidden chat uploads.
10. **Data retention.** Define retention and deletion behavior before activation. Cloud source content, project-authoritative documents, transient research candidates, and model-training datasets remain separate.

## Current API

- `GET /api/cloud/connectors` reports provider names, approved read-only scopes, and setup status.
- It does not reveal environment values, credentials, tokens, account names, or file metadata.
- `connect_enabled` remains false. This must not be changed until user identity, OAuth/PKCE, encrypted token storage, isolation, audit, disconnect, and security tests are in place.

## Safety constraints

- No provider secrets in frontend JavaScript, APKs, source control, logs, or browser storage.
- No use of ChatGPT's own connected Dropbox/OneDrive/Google connectors as if those credentials were available to the FINZANJIR Render server. They are separate authorization contexts.
- No scraping private cloud links or bypassing provider permissions.
- No automatic write operations, public sharing, deletion, or file movement.
- No automatic training or authoritative knowledge promotion from cloud files.
- Bank, customer, identity, credential, and other sensitive data are excluded unless a separately documented legal basis and explicit data-processing approval exist.

## Activation gate

Cloud account linking is not production-ready until the identity and token-security design is implemented and independently reviewed. Provider application registrations and redirect URIs must then be configured as Render secrets/environment settings by the account owner. The first release should be read-only and user-selected-folder only.


## Gmail read-only import

An optional `gmail` service can be selected explicitly during account linking with the `gmail.readonly` scope. FINZANJIR can list message IDs using a bounded Gmail search query and import only a message the owner selects. The message body and limited headers are extracted, encrypted, and saved in the same private quarantine with provider provenance `google_gmail`. HTML-only bodies are converted to text while script/style content is excluded. Attachments are not downloaded by this first implementation.

Gmail read access is a restricted Google OAuth scope and may require Google verification/security assessment before public use. It is never requested by the default Drive-only connection. No compose, send, modify, delete, label, or mailbox settings scopes are requested. See the official Gmail API documentation for read-only scope and message list/get methods: https://developers.google.com/workspace/gmail/api/auth/scopes and https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages.



## Google Photos Picker

Google Photos uses the current Picker API, not the legacy full-library read scopes removed in March 2025. The optional `photos` service requests only `https://www.googleapis.com/auth/photospicker.mediaitems.readonly`. FINZANJIR creates a Picker session, returns Google's `pickerUri` for the owner to open, polls the session using Google's polling configuration, lists only media explicitly selected in that session, and deletes the session after use. See Google's current [Picker API flow](https://developers.google.com/photos/picker/guides/get-started-picker), [sessions.create](https://developers.google.com/photos/picker/reference/rest/v1/sessions/create), and [mediaItems.list](https://developers.google.com/photos/picker/reference/rest/v1/mediaItems/list). The old Library API scopes `photoslibrary.readonly`, `photoslibrary.sharing`, and `photoslibrary` were removed from general-library access after March 31, 2025; FINZANJIR does not request them. [Google Photos API updates](https://developers.google.com/photos/support/updates).

Selected photo and video bytes are downloaded only after explicit selection, with a 100 MiB cap, and encrypted in the owner's private media quarantine with a content hash and Picker session provenance. The returned media base URLs are short-lived and are not stored. The bytes are stored but not yet interpreted by a vision, speech, or video model; that is a separate local multimodal pipeline stage. Picker sessions are owner/account-bound and can be polled, listed, and deleted only from the owner's authenticated session.
