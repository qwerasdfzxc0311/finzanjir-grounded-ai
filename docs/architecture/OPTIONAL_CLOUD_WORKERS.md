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

`JsonHttpWorkerAdapter` provides the generic HTTPS JSON transport. `cloud/providers.py` supplies independent request/response adapters for OpenAI, Anthropic, Gemini, Mistral and Cohere because their APIs use different authentication headers and payloads. A provider is registered only when both its server-side API key and model ID are configured:

- OpenAI: `OPENAI_API_KEY`, `OPENAI_MODEL`
- Anthropic: `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`
- Gemini: `GEMINI_API_KEY`, `GEMINI_MODEL`
- Mistral: `MISTRAL_API_KEY`, `MISTRAL_MODEL`
- Cohere: `COHERE_API_KEY`, `COHERE_MODEL`

Optional endpoint override variables are available in the adapter module for controlled deployments. Model IDs are never hard-coded. Credentials are read from server-side environment variables; prompts, responses and secrets are not logged. Registering an adapter does not make a request: the default-deny `CloudPolicy` and per-task approval still gate every execution.

Before configuring a real provider, assess:
- data-processing terms, retention and model-training use;
- regional availability and data residency;
- subprocessors and deletion controls;
- security certifications and incident notification;
- pricing, quotas, latency and outage behavior;
- the exact categories of data the provider is legally permitted to process.

## Not included

This change does not choose or enable any provider, add credentials, make external calls, train a model, or send any FINZANJIR/customer data to a cloud service. It only creates the replaceable adapter and policy boundary. Real provider integrations are a separate reviewed step.

