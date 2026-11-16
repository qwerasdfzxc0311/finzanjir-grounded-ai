# FINZANJIR Plugin Capability Registry

Status: policy evaluator for a trusted host-provided inventory. It does not enumerate the ChatGPT account, inspect live connections, request new grants, or invoke plugins.

## Host inventory contract

A future host adapter must provide a capability snapshot containing, per plugin:

- stable plugin identifier;
- connected and enabled state;
- explicitly granted permission scopes;
- exposed action identifiers;
- each action's enabled state, declared required scopes, risk class, and preapproval status.

This snapshot must come from the trusted host integration. Never derive it from model-generated JSON, user messages, retrieved documents, or plugin output. Missing or unverifiable fields fail closed.

## Decision rules

1. A plugin must exist in the host inventory, be connected, and be enabled.
2. The requested action must be exposed and enabled.
3. Every action scope and caller-required scope must be present in the granted-scope set.
4. Only public and project-internal data are accepted by this initial policy. Personal, financial, bank, customer, restricted, or unknown classes are denied pending separate legal and privacy review.
5. A preapproved read-only action may proceed without an extra prompt only when all checks pass.
6. Write or external-effect actions require explicit user confirmation for that action, even if the plugin is connected.
7. Unknown action risk, missing inventory, missing scopes, or inconsistent metadata means deny.

Connection is not the same as permission. A plugin being listed or connected does not grant every action. Permission is action- and scope-specific. FINZANJIR may inspect the host's permission snapshot and choose an allowed action, but it cannot grant itself new permissions or widen scopes.

## Execution boundary

This module only returns an allow/deny/confirmation decision. It does not execute anything. A future executor must independently re-check the current host permission snapshot immediately before invocation, enforce tool-specific input schemas, minimize data, log the action, sanitize returned content, and treat all plugin output as untrusted. Revoked or stale permissions must stop execution.

## Current limitation

No ChatGPT plugin inventory or live connection state is currently wired into this repository. Therefore the application cannot yet truthfully display which of the user's ChatGPT plugins are connected. That requires a supported host integration which exposes the inventory and granted scopes; do not scrape credentials or infer permission from installed plugin names.
