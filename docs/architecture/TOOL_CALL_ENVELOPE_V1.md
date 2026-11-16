# FINZANJIR Tool-call Envelope v1

Status: validated request representation only. No tool execution, network access, subprocess, or automatic approval is implemented.

## Envelope

A request is JSON with exactly these fields:

- version: integer 1.
- call_id: 1–64 ASCII letters, digits, underscore, or hyphen.
- tool: a lowercase tool identifier (up to 64 characters).
- arguments: a JSON object.
- data_classification: currently only public or project_internal.
- approval_required: must be the boolean true.

Unknown fields, duplicate JSON keys, unsupported versions, malformed names, non-JSON values, non-finite numbers, oversized payloads, excessive nesting, and excessive value counts are rejected.

## Allowlist and approval

The caller must pass an explicit allowed_tools collection. Its default is empty (deny all). A valid envelope only means that its structure passed validation and the tool name appeared in that caller-supplied allowlist. It does not prove that the caller is authorized to access the data or perform the requested operation.

Explicit user approval remains mandatory. Tool-specific argument schemas, user/role authorization, data minimization, purpose limitation, rate limits, audit logging, output sanitization, and revocation must be implemented and checked by a future execution layer. This module does not implement those controls and must not be treated as a substitute for them.

Sensitive, restricted, personal, bank, and customer data classifications are intentionally not accepted. Do not work around this restriction by relabeling data. Any future expansion requires a separate legal, privacy, and security review.

## Trust boundary

Tool output is untrusted input. It must not silently become authoritative project evidence or override system/developer policy. Tool results need provenance, minimization, validation, and explicit grounding before being shown to users or included in model context.

## Deliberate non-goals

- No tool is enabled by this module.
- No execution, network request, browser operation, filesystem access, or connector call occurs.
- No dynamic tool discovery or model-controlled allowlist changes.
- No credentials, secrets, or API keys are accepted as special fields.
- No developer chat role is introduced; role precedence remains a separate design decision.
