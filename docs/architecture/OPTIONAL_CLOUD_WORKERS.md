# Optional Cloud Worker Adapters

Status: framework only; no provider is enabled or configured by this change.

## Roles

The registry supports five replaceable worker roles:

1. `language` — translation, transliteration, spelling and dialect review.
2. `research` — search approved public sources and return source-backed findings.
3. `critic` — check a local answer for unsupported claims or reasoning errors.
4. `editor` — improve clarity without changing facts.
5. `specialist` — a narrowly scoped task selected by measured need.

Each role may be backed by a different provider. Provider names, endpoints, models and credentials belong in server deployment configuration, not application business logic or the Android APK.

## Default-deny execution

- `CloudPolicy.enabled` defaults to false.
- The task data class defaults to `sensitive`.
- The data class must be explicitly approved by deployment policy.
- Every task requires explicit per-request user approval by default.
- Non-public data additionally requires a deployment-level legal-review allow-list and a non-empty legal-basis reference.
- A conservative identifier deny-list blocks common payment/contact identifiers as an additional guard. It is not full DLP and must not be represented as sufficient legal or privacy protection.
- Only explicitly requested roles execute. A task can reach at most two workers, even if policy is misconfigured with a larger limit.
- Worker outputs are marked untrusted. They are suggestions to be checked against local evidence, never authoritative knowledge.

## Adapter contract

`JsonHttpWorkerAdapter` provides a generic HTTPS JSON transport. Each provider integration supplies its own request and response mappers because providers do not share a universal API contract. Credentials are read from server-side environment variables; prompts, responses and secrets are not logged.

Before configuring a real provider, assess:
- data-processing terms, retention and model-training use;
- regional availability and data residency;
- subprocessors and deletion controls;
- security certifications and incident notification;
- pricing, quotas, latency and outage behavior;
- the exact categories of data the provider is legally permitted to process.

## Not included

This change does not choose or enable any provider, add credentials, make external calls, train a model, or send any FINZANJIR/customer data to a cloud service. It only creates the replaceable adapter and policy boundary. Real provider integrations are a separate reviewed step.

