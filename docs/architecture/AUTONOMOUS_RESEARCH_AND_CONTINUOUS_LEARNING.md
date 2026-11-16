# FINZANJIR Autonomous Research and Continuous Learning

## Product requirement

FINZANJIR should make useful progress when no person is actively chatting with it. This is autonomous research, not permission for uncontrolled self-modification.

## Operating modes

1. **Offline autonomous mode:** process the local approved corpus and cached public evidence, deduplicate, prepare index updates, detect stale records, run evaluations, and prepare research questions. It creates no external network traffic. The engine requires a local-only `OfflineEvidenceAdapter`; it does not call online discovery or fetch adapters in this mode.
2. **Online autonomous mode:** on a host-approved schedule, discover and fetch public information from explicitly configured source domains. The host must expose a visible online toggle, network budget, source allowlist, schedule, pause/resume, and audit log.
3. **Interactive mode:** answer a user with the same source/provenance rules.

Live Internet access necessarily creates network traffic. No hidden telemetry or user-chat upload is allowed.

## Research cycle

`AutonomousResearchEngine` is a policy-controlled orchestration primitive. A host scheduler may run it periodically after explicit configuration. Each cycle is bounded by approved categories, source/domain allowlists, source/item/byte budgets, deduplication, and quarantine. The host scheduler and persistent store must enforce per-source refresh intervals, rate limits, and durable audit records; these are not yet implemented in this module.

The module is disabled by default and does not create a scheduler or run in the background by itself. A trusted host must provide scheduler, adapters, persistent storage, and user-visible controls. Online adapters must enforce transport-level streaming byte limits and safe URL validation before connecting.

## What can be researched

Examples include public science, astronomy, chemistry, languages, history, geography, technology, software security advisories, CVEs, official CERT notices, vendor bulletins, and academic publications, subject to source terms and licensing. This is not an unrestricted crawler. The source registry must state allowed categories, domains, licensing, reliability, freshness, and contact/owner.

## Knowledge lifecycle

Discovered -> fetched or read from cache -> quarantined -> source/licence/content and sensitive-data review -> approved candidate -> indexed knowledge -> eligible for later training review.

External material is untrusted. Human reviewers must verify source, licence, quality, and sensitive-data status. Sensitive personal, bank, customer, credential, and restricted data are excluded. Evidence, project-authoritative documents, and training corpora remain separate.

## Model learning versus knowledge learning

- Knowledge learning: safe collection, indexing, retrieval, and evidence updates. It can progress without retraining weights.
- Model training: changes parameters. It must be a separate, versioned, reproducible pipeline with reviewed/licensed datasets, train/validation/test splits, evaluation gates, rollback, and compute approval. Never update weights continuously from unreviewed internet content.

The model cannot add domains, grant itself network access, approve its own evidence, change its safety policy, or train itself outside the governed pipeline.

## Threat-intelligence use

The system can identify and correlate public indicators (domains, URLs, hashes, CVEs, published IP indicators) and explain confidence, provenance, and expiry. Indicators are leads, not proof of criminal conduct. No automatic blocking, accusation, or law-enforcement action.

Direct darknet/onion access is not included. Public reporting about darknet threats is preferred. Any future isolated Tor research requires separate legal and security review and cannot involve transactions, illegal content acquisition, credential theft, exploitation, or evasion.

## Human supervision

The system can operate unattended only within a preapproved read-only budget and scope. Human review is required for source approval, licence acceptance, sensitive-data assessment, promoting content into authoritative knowledge, training-set inclusion, model weight updates, and consequential actions. Maintain logs and pause safely on policy violations or uncertainty.

## Implementation status

This PR adds policy and orchestration primitives only. It does not connect a real scheduler, source registry, online/offline storage adapter, user interface, or model training job. These are separate integration steps and must be tested before claiming unattended operation is live.
