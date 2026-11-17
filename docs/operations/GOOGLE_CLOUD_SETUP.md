# Google Cloud setup for FINZANJIR

This runbook is for the single configured FINZANJIR owner. Never paste Google client secrets, refresh tokens, session secrets or encryption keys into chat, source files, GitHub issues or browser storage.

## 1. Google Cloud Console

Create a Google Cloud project and configure the OAuth consent screen as an external or internal app according to the owner's account type. Add the owner and every Google account that will be linked as test users while the app is in Testing mode. For long-lived unattended access, the app must meet Google's publishing, verification and any restricted-scope security-assessment requirements; test-mode refresh tokens can expire.

Create an OAuth client of type **Web application**. Add this exact authorized redirect URI:

```
https://finzanjir-grounded-ai-api.onrender.com/api/google/oauth/callback
```

Enable the Google Drive API and Gmail API. Enable Google Photos Picker API for the explicit selected-media flow. Request only the service scopes the owner intends to use.

## 2. Render environment

Set these only in the private API service's environment settings, never in the static frontend:

- `FINZANJIR_GOOGLE_CLIENT_ID`
- `FINZANJIR_GOOGLE_CLIENT_SECRET`
- `FINZANJIR_GOOGLE_REDIRECT_URI=https://finzanjir-grounded-ai-api.onrender.com/api/google/oauth/callback`
- `FINZANJIR_OWNER_EMAIL`
- `FINZANJIR_SESSION_SECRET` (at least 32 cryptographically random bytes)
- `FINZANJIR_TOKEN_ENCRYPTION_KEY` (generate using Fernet key generation; keep stable and back it up securely)
- `FINZANJIR_GOOGLE_STATE_DB_PATH` (absolute path on a persistent private disk)
- `FINZANJIR_PERSONAL_MEMORY_DB_PATH` (absolute path on a persistent private disk)
- `FINZANJIR_FRONTEND_URL` (the exact deployed static frontend origin, HTTPS only)
- `FINZANJIR_ALLOWED_ORIGINS` (comma-separated exact origin allowlist; must contain the frontend origin)

The API currently has two historical static frontend service names in Render. Confirm which one is the intended public frontend before setting `FINZANJIR_FRONTEND_URL`; do not add wildcard origins.

## 3. Before enabling real accounts

- Confirm both database paths are mounted on persistent encrypted storage and are backed up.
- Confirm the token-encryption key and session secret are stored as Render secrets and are recoverable only by the owner/operator.
- Confirm Google OAuth consent, APIs, redirect URI and requested scopes in Google's console.
- Start with one Google account and a small number of selected files/messages/media.
- Verify owner login, account isolation, disconnect/revoke, import audit, restart recovery and backup restore.
- Only then add the remaining accounts, one by one, up to the 100-account cap.

## 4. Product limitations

- Google Photos Picker grants access to items the owner explicitly selects in each Picker session. It is not an API for silently reading the entire Google Photos library. For a full archive, use Google Takeout and a separately reviewed archive-import pipeline.
- Imported media bytes are encrypted and retained, but local image understanding, speech transcription and video summarization are not implemented until FINZANJIR has its own reviewed local multimodal models.
- Imported text remains quarantined and searchable by the owner; it is not yet injected into the FINZANJIR project-answer knowledge base.

## 5. Current Render persistence gate (reviewed 2026-11-17)

The current `finzanjir-grounded-ai-api` Render service is on the **Free** compute plan. Free web services have an ephemeral filesystem and cannot attach persistent disks. A directory such as `/var/data` does not make SQLite durable; its contents can be lost on restart, spin-down or redeploy.

Therefore:
- Do not enable real Google OAuth imports or unattended research on the current Free API service.
- Before importing personal files, select a durable storage design: a paid single-instance API with a persistent disk for SQLite, or a managed durable database plus private object storage for encrypted media. A Render Free Postgres instance is not a long-term substitute because it expires after 30 days.
- The 100 MiB media import ceiling is a per-file safety bound, not a storage capacity promise. For a large Photos/Drive archive, move encrypted media blobs out of SQLite into private object storage and keep only metadata, hashes, provenance and search indexes in the database.
- The autonomous research daemon also needs its own supported Background Worker compute and durable state store. It is not running merely because the Python entrypoint exists.
- Re-run the Settings diagnostics after storage is configured. It must report the actual mounted disk or datastore readiness, not merely the presence of a directory.

No Render plan, disk, database, service, or environment variable is changed by this PR. Obtain explicit owner approval before making any cost-bearing infrastructure change.
