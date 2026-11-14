# Sanitized LLM Provider Failure Diagnostics v1

## Why this exists

The live 50-question synthetic benchmark returned HTTP 200 for every request, but 44 responses reported `provider_failed`. The public answer contract intentionally does not expose provider response bodies, exception strings, API keys, prompts, or user text. That privacy boundary must remain.

The gateway already classifies failures internally. The missing piece is a safe operational signal in server logs so an operator can distinguish authentication/permission failures, rate limits, provider outages, timeouts, network failures, rejected requests, and invalid provider responses.

## Logging behavior

When a configured provider attempt fails, the gateway writes one warning containing only:

- provider name from the fixed allowlist (`gemini` or `openrouter`)
- sanitized failure category from the gateway's fixed categories

It does **not** log:

- API keys or authorization headers
- user questions, prompts, or model responses
- provider response bodies
- raw exception text or stack traces

A fallback provider may still succeed after the primary provider fails. In that case the failed primary attempt is logged, while the final request status remains successful.

## Failure categories

- `authentication_or_permission_failed`
- `rate_limited`
- `provider_unavailable`
- `timeout`
- `network_error`
- `request_rejected`
- `invalid_response`

No provider keys, environment values, or configuration secrets are changed by this feature.

## Verification

A regression test injects a synthetic 401 response containing secret-bearing body text and asserts that logs include the provider/category but exclude the response text, test key, prompt, and user text.

## Scope and limitations

This change improves observability only. It does not change provider selection, retry order, timeouts, prompts, model choice, answer generation, or fallback behavior. It cannot repair an invalid key or provider outage by itself. After a controlled deploy, operators can inspect sanitized Render logs and decide the next corrective action based on observed categories.
