# FINZANJIR Cloudflare runtime

This Worker is the first durable coordination layer. It is deliberately fail-closed:
- D1 stores runtime state, queue metadata, audit events and backup manifests.
- The Cron supervisor advances a persisted 60-minute work / 10-minute rest state machine in short invocations. It does not run one continuous 60-minute process.
- It does not import personal content, process bank data, call external AI services, or expose job payloads.
- R2 is not yet enabled in the owner account. No media import or backup mirror is enabled until R2, encryption/key recovery, authenticated API integration and restore tests are complete.
- The public health route returns service readiness only and no personal information.

Apply the migration before deploying:
```sh
wrangler d1 migrations apply finzanjir-memory-v1 --remote
wrangler deploy
```

Free-plan execution is only a scheduler/coordinator. OCR, transcription, media understanding, web research and model inference require separate bounded providers/compute and explicit configuration.
