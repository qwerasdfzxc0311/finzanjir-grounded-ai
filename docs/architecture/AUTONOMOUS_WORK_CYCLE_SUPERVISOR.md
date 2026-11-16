# FINZANJIR autonomous work-cycle supervisor

## Implemented mechanism

`AutonomousCycleSupervisor` is a host-invoked asynchronous worker supervisor. It is not a hidden always-on process: the host must explicitly enable it, provide approved task handlers, and run `run_forever`.

Defaults:
- Up to 60 minutes of work per cycle.
- 10-minute rest after each cycle.
- A 5-minute renewable lease, renewed after every successful worker step.
- Worker step timeout no longer than half the lease, so a stalled step is cancelled before another process can safely reclaim the lease.
- Maximum 500 steps per cycle.
- Checkpoints are JSON objects capped at 64 KiB.
- Failed or interrupted work keeps the last committed checkpoint; a later cycle resumes from it.
- Completed work clears its checkpoint and records an audit event.
- Pause/disable is checked between steps; disabled jobs are not claimed.
- Jobs remain disabled unless explicitly enabled by the host/operator.

## Worker contract

A handler receives the last saved checkpoint and remaining time budget, then returns a `WorkStep` containing the next checkpoint, completion flag, and bounded counters. The supervisor persists each checkpoint before moving to the next step. Handlers must be idempotent because a process can fail after an external read but before its checkpoint is committed.

## Persistence and deployment

The runtime store requires a durable filesystem path. Ephemeral container filesystems are not suitable for long-term unattended work. A production host must mount persistent storage, configure backups/retention, and explicitly start one supervisor instance. SQLite leases prevent ordinary duplicate execution across processes sharing the same database; use a database with stronger coordination if deployment moves to multiple hosts or regions.

## Safety boundaries

The supervisor does not itself browse the web, access private accounts, execute arbitrary shell commands, train model weights, or promote research candidates. Those capabilities must be supplied as separately reviewed handlers and remain governed by their own source, network, data-class, and approval policies. A checkpoint is progress state, not permission to continue a previously denied action.


## Opt-in public research worker

The worker can be started with:

```bash
python -m finzanjir_ai.intel.worker_daemon
```

It exits without running if `FINZANJIR_AUTONOMOUS_RESEARCH_ENABLED` is not true. Online research additionally requires `FINZANJIR_AUTONOMOUS_RESEARCH_ONLINE_ENABLED=true`, `TAVILY_API_KEY`, an absolute durable `FINZANJIR_RESEARCH_DB_PATH`, and an operator-supplied `FINZANJIR_RESEARCH_SOURCES_JSON` array. Each source contains a unique `source_id`, a non-personal public research `query`, an explicit `allowed_domains` list, and an `enabled` boolean.

Example source configuration:

```json
[
  {
    "source_id": "public-cyber-advisories",
    "query": "latest public cybersecurity advisories and defensive mitigations",
    "allowed_domains": ["cisa.gov", "nvd.nist.gov"],
    "enabled": false,
    "interval_minutes": 60
  }
]
```

The worker sends only the configured query to Tavily, asks the provider to return bounded raw extracts, rejects result URLs outside the exact domain allowlist, and stores results as untrusted quarantined candidates. It does not directly connect to arbitrary result URLs from the worker host. Each candidate is idempotently keyed by source, URL and content hash; a process restart can safely repeat a search batch without duplicating the same candidate. The supervisor writes a checkpoint after each worker step and keeps failed work quarantined.

The daemon is a separate process entrypoint, not part of the API startup. Before starting it in production, provision a durable encrypted disk, configure the allowlisted topics/domains and API key, inspect the service logs/health, and explicitly enable both switches. No Render Background Worker service is created or enabled by this PR.
