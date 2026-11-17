# FINZANJIR secure cloud connectors

## Goal

Allow FINZANJIR to discover and read approved project knowledge in user-authorized cloud stores while keeping each user's files private, traceable, and separate from FINZANJIR's authoritative project corpus and training datasets.

## Current implementation status (verified 2026-11-17)

This repository contains a **partial Google single-owner connector**, not a fully implemented multi-provider cloud connector.

- **Google Drive:** OAuth Authorization Code + PKCE, owner session, account registry, file listing, selected document import and selected binary-media import are implemented. The code currently requests `https://www.googleapis.com/auth/drive.readonly`.
- **Gmail:** bounded message listing and owner-selected message import are implemented with `https://www.googleapis.com/auth/gmail.readonly`. No send, compose, modify, label or mailbox-management scope is requested.
- **Google Photos:** the current Picker API is implemented. Only media selected in a Picker session is listed/imported, using `photospicker.mediaitems.readonly`.
- **Dropbox and Microsoft OneDrive:** only provider policy/readiness descriptions exist. OAuth, token storage, import, revocation and account isolation are not implemented for these providers; they must remain disabled.
- Google refresh tokens are encrypted server-side using the configured Fernet key. Owner sessions use a signed HttpOnly/Secure/SameSite=Lax cookie. The implementation is single-owner, not multi-tenant.
- Imported Google text and media are stored in a private, owner-scoped quarantine with provenance and audit metadata. They are not automatically added to the canonical project corpus or training data. The current `/api/ai/answer` path does not yet use this quarantine as a separate personal-memory context.
- OAuth routes fail closed when required configuration is missing. The current Render Free service has ephemeral storage, so the code existing in the repository does not mean real-account imports are safe to enable in the current deployment.

## Google OAuth scope and policy gate

The actual scopes in `src/finzanjir_ai/integrations/google_cloud.py` must be described accurately:

| Service | Current scope | Effective access and status |
|---|---|---|
| Drive | `https://www.googleapis.com/auth/drive.readonly` | Read/download **all** Drive files. Google classifies it as restricted. Selecting one file in FINZANJIR's import UI does not reduce the token's underlying scope. |
| Gmail | `https://www.googleapis.com/auth/gmail.readonly` | View email messages and settings. Google classifies it as restricted. FINZANJIR imports only a selected message, but the granted scope is broader than that single message. |
| Photos | `https://www.googleapis.com/auth/photospicker.mediaitems.readonly` | Access media selected by the owner in a specific Picker session; it does not grant silent full-library access. |

Google recommends the narrowest scope needed. For Drive, `drive.file` with Google Picker can provide per-file access, while the current `drive.readonly` scope can read/download all files. Moving to `drive.file` would change which files the integration can discover and import, so it is a separate product/design decision and must not be silently substituted.

Google states that restricted-scope apps require verification unless an exception applies, and apps that store or transmit restricted-scope data through a server require a security assessment by an approved assessor unless an applicable exception is confirmed. The Drive and Gmail use cases, public-app eligibility, data retention, user notice, and security-assessment requirements must therefore be confirmed before public activation. In particular, FINZANJIR's Gmail-to-private-memory import must be checked against Google's approved Gmail use cases; do not assume that read-only access alone makes the use case eligible.

References:
- Google Drive scopes and least-privilege guidance: https://developers.google.com/workspace/drive/api/guides/api-specific-auth
- Google Gmail scopes: https://developers.google.com/workspace/gmail/api/auth/scopes
- Google restricted-scope verification and server-side security assessment: https://developers.google.com/identity/protocols/oauth2/production-readiness/restricted-scope-verification
- Google Photos Picker authorization: https://developers.google.com/photos/overview/authorization

## Remaining production controls and work

1. **Durable storage:** move OAuth state, account/session data, personal-memory records and encrypted media to a verified persistent store with backup/restore tests. Do not enable real imports on the current ephemeral Render Free filesystem.
2. **Scope approval:** complete Google OAuth verification and any required restricted-scope security assessment. Decide explicitly whether Drive's broad `drive.readonly` scope is acceptable or whether the product should move to per-file `drive.file` + Picker.
3. **Gmail use-case approval:** confirm the proposed message-import/personal-memory workflow is permitted by Google's Gmail user-data policy before public use.
4. **Key management:** the current code reads a Fernet key from server environment configuration. A managed key/KMS lifecycle, rotation and recovery process remain to be designed and tested for production.
5. **Personal-memory lifecycle:** add explicit owner review/approval/rejection/revocation states before any private source can be used as approved personal memory. Never promote it automatically into FINZANJIR's authoritative project corpus.
6. **Multi-user isolation:** the current connector is for one configured owner. A multi-user product requires a separate identity, tenant isolation, authorization and audit design.
7. **Other providers:** implement Dropbox and OneDrive OAuth/PKCE, token encryption, least-privilege scopes, import, revocation, audit and isolation before showing them as connected.
8. **Background sync:** no unattended sync should run until a supported scheduler, per-owner quotas, backoff, retention and pause controls exist.
9. **Multimodal understanding:** imported image/audio/video bytes are stored with provenance, but local vision, transcription and video understanding are not implemented.

## Current API

- `GET /api/cloud/connectors` reports safe provider readiness/policy information; it does not expose credentials, tokens, account names or file metadata and is not proof that Google OAuth is active.
- Google owner flows are under `/api/google/*`: OAuth start/callback, account listing/disconnect, Drive listing/import, Gmail listing/import, Photos Picker sessions/import, private-memory source/search/media/audit and diagnostics.
- Google account operations require the configured owner session. State-changing actions also validate the request Origin against the exact configured allowlist.
- Imported content remains owner-scoped and quarantined; it is not automatically promoted to the authoritative project corpus.

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

Gmail read access uses the restricted `gmail.readonly` scope. Public use requires the applicable Google verification and, where restricted data is stored/transmitted server-side, a security assessment unless an exception is confirmed. It is never requested by the default Drive-only connection. No compose, send, modify, delete, label, or mailbox-management scopes are requested. The planned import of messages into FINZANJIR private memory must be checked against Google's approved Gmail use cases before activation. See the official Gmail API documentation for read-only scope and message list/get methods: https://developers.google.com/workspace/gmail/api/auth/scopes and https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages.



## Google Photos Picker

Google Photos uses the current Picker API, not the legacy full-library read scopes removed in March 2025. The optional `photos` service requests only `https://www.googleapis.com/auth/photospicker.mediaitems.readonly`. FINZANJIR creates a Picker session, returns Google's `pickerUri` for the owner to open, polls the session using Google's polling configuration, lists only media explicitly selected in that session, and deletes the session after use. See Google's current [Picker API flow](https://developers.google.com/photos/picker/guides/get-started-picker), [sessions.create](https://developers.google.com/photos/picker/reference/rest/v1/sessions/create), and [mediaItems.list](https://developers.google.com/photos/picker/reference/rest/v1/mediaItems/list). The old Library API scopes `photoslibrary.readonly`, `photoslibrary.sharing`, and `photoslibrary` were removed from general-library access after March 31, 2025; FINZANJIR does not request them. [Google Photos API updates](https://developers.google.com/photos/support/updates).

Selected photo and video bytes are downloaded only after explicit selection, with a 100 MiB cap, and encrypted in the owner's private media quarantine with a content hash and Picker session provenance. The returned media base URLs are short-lived and are not stored. The bytes are stored but not yet interpreted by a vision, speech, or video model; that is a separate local multimodal pipeline stage. Picker sessions are owner/account-bound and can be polled, listed, and deleted only from the owner's authenticated session.


## Drive binary media import

In addition to document extraction, an owner-selected Drive file can be imported as a binary image, audio or video item. The server validates the declared MIME type against supported container signatures (Pillow image verification, WAV/MP3/FLAC/OGG audio headers, MP4/MOV, Matroska/WebM and AVI signatures), applies a 100 MiB cap and a 40-megapixel image limit, then encrypts the bytes into the same owner-only media quarantine. Unsupported types and mismatched content are rejected. This stage preserves the media and provenance; it does not claim to transcribe audio or semantically understand images/video.


## Browser session and CORS requirements

Owner sessions use HttpOnly/Secure cookies. Browser calls from the static frontend must use `credentials: "include"`; the API permits credentialed CORS only for the exact origins listed in `FINZANJIR_ALLOWED_ORIGINS` (comma-separated, no wildcard). The same allowlist is also checked by the server-side Origin/CSRF guard on state-changing actions. Add the exact deployed frontend origin(s) to that setting before enabling Google login. No wildcard credentialed CORS is permitted.

Additional browser OAuth settings:
- `FINZANJIR_FRONTEND_URL`: exact HTTPS frontend origin (no path/query).
- `FINZANJIR_ALLOWED_ORIGINS`: comma-separated exact origin allowlist containing `FINZANJIR_FRONTEND_URL`.
The OAuth callback redirects to this configured frontend. Without both values, Google OAuth fails closed. Credentialed CORS and the CSRF Origin check use this allowlist.

XLSX and DOCX archives are inspected before parsing: at most 2,000 ZIP entries, 100 MiB total expanded content, 50 MiB per entry, a 200:1 compression-ratio ceiling and no absolute or parent-traversal paths. Google Sheets are exported as XLSX so all worksheets can be read, subject to a 100-sheet and 100,000-cell cap.


## Unified memory audit and frontend

The private memory panel in the frontend supports owner Google sign-in, adding accounts/services, Drive document and media import, Gmail message import, Google Photos Picker selection, local encrypted-text search, source/media inventory, and recent import audit events. Browser requests include the owner session cookie; exact frontend CORS and CSRF allowlists are required. Import audit rows record action, provider, account ID, a hash of the remote object ID, content hash and safe file metadata; they never record the document body or search query.

Gmail attachments are limited to 20 per message, 10 MiB each and 50 MiB total per import. Unsupported formats are reported as skipped; supported text documents are extracted and media is stored encrypted. Attachment IDs and source message IDs remain attached to provenance.
