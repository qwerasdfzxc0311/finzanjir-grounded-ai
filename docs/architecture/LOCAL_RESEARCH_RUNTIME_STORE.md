# Local Autonomous Research Runtime Store

## Purpose

Provide a persistent, local-only foundation for future unattended research. This layer records approved job schedules, pause/resume state, execution leases, quarantined evidence, and audit events.

## Safety defaults

- Jobs are disabled unless explicitly enabled by the host/user.
- Minimum supported cadence is one hour; the store does not start a timer or worker.
- A job lease prevents two host workers from running the same job concurrently.
- Pause clears an active lease; resume makes the job eligible from the supplied timestamp.
- All fetched content remains quarantined. This store does not approve, index as authoritative, or train on it.
- SQLite file permissions are restricted to the owner where the operating system supports it.
- The store is local-only; no API, network client, cloud sync, or telemetry is included.

## Host integration contract

A future trusted host scheduler should:
1. Read enabled due jobs.
2. Atomically claim a job lease before starting work.
3. Select only preapproved source IDs and apply the autonomous research policy.
4. Save each candidate to quarantine with its source mode.
5. Finish the job with counters and a concise result; the store records an audit event and computes the next due time.
6. Expose enable, disable, pause, resume, and audit controls to the user.

A crashed worker leaves a lease that expires within the configured maximum of one hour; another worker can then reclaim it. The host must still enforce process-level shutdown and cancellation.

## Not implemented here

No background scheduler, OS service, Android foreground service, cloud deployment, internet connection, source registry, or model training is started. The runtime store is a persistence primitive only. Actual unattended operation requires a host integration, explicit configuration, and separate end-to-end tests.
