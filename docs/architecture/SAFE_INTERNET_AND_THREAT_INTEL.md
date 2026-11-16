# FINZANJIR Safe Internet and Threat-Intelligence Integration

## Purpose

Provide a read-only research path for public cyber-threat information while
preserving an offline-first core. This is a source-evidence capability, not an
autonomous investigator, law-enforcement system, or blocking engine.

## Two operating modes

- **Offline:** search the local evidence cache and approved project corpus.
  No network connection is attempted and no content leaves the device.
- **Online:** retrieve bounded public text from HTTPS domains explicitly
  configured by an administrator. Each record retains URL, retrieval time,
  content type, and SHA-256 digest. The default domain allowlist is empty.

A cache is not automatically trusted forever: records should be revalidated
against source freshness and provenance before being used as current evidence.

## Initial implementation

`finzanjir_ai.intel.public_web` provides:
- explicit HTTPS domain allowlisting;
- public-address resolution checks;
- redirects, credentials, unusual ports, local/private destinations and
  unsupported content types blocked;
- bounded response size and timeout;
- SQLite evidence cache usable offline;
- source URL, retrieval timestamp, content type and digest retained.

This is a small safe retrieval primitive. It is not yet wired into the chat UI,
scheduler, search engine, source registry, or production deployment. No
background crawling is enabled.

## Threat-intelligence source categories

A later reviewed source registry may include:
- official national CERT and regulator advisories;
- CISA, NCSC and other public government advisories;
- vendor security bulletins and CVE/NVD records;
- public malware/domain/IP reputation feeds whose terms permit use;
- public research from universities and recognized incident responders.

Every source needs an owner, permitted-use/license note, update cadence,
reliability rating, and review status. Treat fetched pages as untrusted data:
never execute scripts, binaries, macros, or instructions found in them.

## Tor and onion services

Tor transport and .onion access are **not implemented or enabled** by this
change. The repository must not silently install Tor, change system proxy
settings, or route all device traffic through Tor.

A future isolated research adapter would require a separately approved
deployment, explicit legal and safety review, strict read-only collection,
no account creation or purchases, no interaction with illegal services, no
downloads of illegal material, no credential harvesting, no exploitation,
and no attempts to evade law enforcement or access controls. Prefer public
threat-intelligence reporting about darknet activity over direct visits to
onion marketplaces. Any collected indicators must be independently validated.

## Detection and use constraints

- Indicators are leads, not proof that a person committed a crime.
- Do not identify or accuse private individuals from an IP address, handle,
  wallet, phone number, or single indicator.
- No automatic account/card blocking, reporting to authorities, or other
  consequential action.
- Require human review, corroborating evidence, confidence/uncertainty labels,
  timestamps, and an auditable reason before any downstream action.
- Do not ingest personal, bank, customer, or confidential data without a
  documented legal basis and approved minimization process.
- Keep the threat-intel corpus separate from FINZANJIR project-authoritative
  documents and from future model-training datasets. Training requires
  independent licensing, quality review, deduplication, and approval.

## Network and privacy model

Online retrieval necessarily creates network traffic to the configured source.
The offline mode creates no external traffic. The system cannot provide both
live internet access and zero network traffic at the same moment. To minimize
exposure, online mode sends only the requested public URL and standard HTTP
metadata; it must never transmit user prompts, chat history, personal data, or
bank data.

## Remaining integration work

1. Add a reviewed source registry and freshness policy.
2. Add an evidence search/index layer and citations in the answer contract.
3. Add trusted host controls for online/offline switching and visible network
   status.
4. Add operator-configured source allowlists and rate limits.
5. Add tests for DNS rebinding, redirects, malformed responses, stale cache,
   and source provenance.
6. Only after separate approval, assess whether a legally compliant isolated
   Tor research environment is necessary. No Tor/onion access is part of the
   current implementation.
