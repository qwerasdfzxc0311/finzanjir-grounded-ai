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
