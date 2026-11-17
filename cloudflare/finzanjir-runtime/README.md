# FINZANJIR runtime Worker

This directory contains the source of the existing `finzanjir-runtime` Cloudflare Worker, captured read-only from the currently deployed Worker script on 2026-11-17.

## Important

- This source is version-control recovery, not a new deployment.
- Preserve the existing supervisor behavior, D1 `runtime_state` / `runtime_jobs` / `runtime_audit` / `backup_manifests` schema, and existing five-minute Cron trigger.
- The current Worker exposes only `GET /` and `GET /health`; all other paths return 404.
- Personal-data import is deliberately disabled in the current Worker.
- Do not add personal-memory endpoints to this Worker until the exact deployed settings, bindings, migrations, authentication, backup/restore, and replay protections have been reviewed.
- Do not deploy this source automatically. First compare it with the live script and its settings (compatibility date, D1 binding, Cron schedule, routes, limits, and secrets). The D1 binding and secret values must never be committed.
- The existing supervisor tables are not to be repurposed for user data. New application tables must use a separate namespace and versioned migrations.

## Verification still required before deployment

1. Compare the committed source byte-for-byte with the live Worker source.
2. Capture non-secret settings and binding metadata; never retrieve or print secret values.
3. Add a local Worker test harness for health, 404, lease contention, work/rest transitions, and audit writes.
4. Rehearse D1 migrations and restore against a separate test database.
5. Review authentication, authorization, HMAC replay defense, rate limits, data retention, and deletion before adding application APIs.
