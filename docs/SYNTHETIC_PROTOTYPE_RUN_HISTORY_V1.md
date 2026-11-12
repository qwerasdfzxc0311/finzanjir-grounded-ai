# Synthetic Prototype Run History v1

## Purpose

Keep a small, inspectable history of prototype executions across application process restarts without persisting transaction-level or identity data.

## Stored data

The SQLite table `prototype_run_history` stores only:
- generated run ID and timestamp;
- explicit `synthetic` data mode;
- risk score and risk level;
- active threshold;
- counts of signals, evidence items and independent signal families;
- case eligibility/opened and Shadow Mode flags;
- risk engine and signal registry versions.

The history deliberately excludes transaction IDs, bank/customer identifiers, account/card numbers, device/network identifiers, raw signal events and raw evidence payloads. API response for the immediate run remains the detailed synthetic execution response; the history endpoint returns only the minimized summary.

## API

- `GET /api/prototype/runs?limit=50` returns up to 100 recent aggregate summaries.
- `POST /api/prototype/run` saves a summary after the synthetic run succeeds.
- Retention defaults to 30 days; expired summaries are deleted on save and list operations.

## Storage configuration

Default local path: `var/finzanjir-prototype.sqlite3`.

Override with:

```bash
FINZANJIR_PROTOTYPE_DB_PATH=/var/data/finzanjir-prototype.sqlite3
```

The database file is created with restrictive POSIX permissions where supported. SQLite WAL is used for local same-host reader/writer concurrency. SQLite WAL must not be placed on a network filesystem.

## Deployment limitation

A container host with an ephemeral filesystem can lose this history during redeploy/restart. To retain it on a hosted prototype, configure a persistent disk mounted on the same host and point `FINZANJIR_PROTOTYPE_DB_PATH` to that mount. Do not assume the Render service currently has a persistent disk attached. Multi-instance deployments should use a managed database instead of a shared SQLite WAL file.

## Safety boundary

This is synthetic prototype history, not the authoritative FINZANJIR case/audit ledger. It does not store real customer data and must not be enabled for real transaction data without a separate legal basis, data protection assessment, authentication/RBAC, key management, retention approval and bank integration controls.


## Runtime visibility

The history API returns a `persistence_note` and the frontend displays it. A successful SQLite write does not prove durable hosted persistence: an ephemeral service filesystem can lose the history after restart or redeploy. A persistent disk or managed database must be verified before describing hosted run history as durable.
