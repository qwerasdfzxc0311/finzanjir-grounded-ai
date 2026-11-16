# FINZANJIR Autonomous Research and Continuous Learning

## Product requirement

FINZANJIR should be able to make useful progress when no person is actively
chatting with it. This is an autonomous research capability, not permission
for uncontrolled self-modification.

## Operating modes

1. **Offline autonomous mode:** process the local approved corpus, cached
   public evidence, deduplicate, index, detect stale records, run evaluations,
   and prepare research questions. It creates no external network traffic.
2. **Online autonomous mode:** on a host-approved schedule, discover and fetch
   public information from explicitly configured source domains. The host
   must expose a visible online toggle, network budget, source allowlist,
   schedule, pause/resume, and audit log.
3. **Interactive mode:** answer a user, with the same source/provenance rules.

Online and offline modes are mutually exclusive for a given retrieval action.
Live Internet access necessarily creates network traffic. No hidden telemetry
or user-chat upload is allowed.

## Research cycle

`AutonomousResearchEngine` is a policy-controlled orchestration primitive.
A host scheduler may run it periodically after explicit configuration. Each
cycle is bounded by:
- approved source categories and source-specific domain allowlists;
- maximum sources, items, bytes, and request duration;
- per-source refresh intervals and rate limits;
- deduplication by canonical URL and content digest;
- quarantine of all external material;
- an audit record with source, timestamp, content hash, and processing result.

The module is disabled by default and does not create a scheduler or run in
the background by itself. A trusted host must provide scheduler, adapters,
persistent storage, and user-visible controls.

## What can be researched

Examples include public science, astronomy, chemistry, languages, history,
geography, technology, software security advisories, CVEs, official CERT
notices, vendor bulletins, and academic publications, subject to source
terms and licensing. This is not an unrestricted crawler. The source registry
must state allowed categories, domains, licensing, reliability, freshness,
and contact/owner.

## Knowledge lifecycle

Discovered -> fetched -> quarantined -> source/licence/content review ->
approved candidate -> indexed knowledge -> eligible for later training review.

A candidate is never promoted simply because a model says it is true. Source
verification, licence approval, deduplication, quality checks, and human
review are required. Sensitive personal, bank, customer, credential, and
restricted data are excluded. Keep evidence, project-authoritative documents,
and training corpora separate.

## Model learning versus knowledge learning

- Knowledge learning: safe collection, indexing, retrieval, and evidence
  updates. Can progress without retraining model weights.
- Model training: changes parameters. It must be a separate, versioned,
  reproducible pipeline with reviewed/licensed datasets, train/validation/test
  splits, evaluation gates, rollback, and compute approval. Never update
  weights continuously from unreviewed internet content.

The model may generate research questions and propose source categories, but
it cannot add domains, grant itself network access, approve its own evidence,
change its own safety policy, or train itself without the governed pipeline.

## Threat-intelligence use

The system can identify and correlate public indicators (domains, URLs,
hashes, CVEs, published IP indicators) and explain confidence, provenance,
and expiry. Indicators are leads, not proof of criminal conduct. No automatic
blocking, accusation, or law-enforcement action.

Direct darknet/onion access is not included. Public reporting about darknet
threats is preferred. Any future isolated Tor research requires separate
legal and security review and cannot involve transactions, illegal content
acquisition, credential theft, exploitation, or evasion.

## Human supervision

Human review is required for source approval, licence acceptance, promoting
content into authoritative knowledge, training-set inclusion, model weight
updates, and consequential actions. The system can operate unattended within
its preapproved read-only budget and scope, while maintaining logs and
pausing safely on policy violations or uncertainty.

## Implementation status

This PR adds policy and orchestration primitives only. It does not connect a
real scheduler, source registry, online adapter, user interface, or model
training job. Those are separate integration steps and must be tested before
claiming unattended operation is live.
