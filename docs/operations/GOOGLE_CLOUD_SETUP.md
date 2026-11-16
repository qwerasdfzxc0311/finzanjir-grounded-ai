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
