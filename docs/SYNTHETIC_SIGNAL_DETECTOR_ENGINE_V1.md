# FINZANJIR Synthetic Signal Detector Engine v1

## Purpose and boundary

This release turns the existing 40-signal registry into executable, data-driven candidate rules for synthetic feature bundles. It is a development/test harness for the FINZANJIR signal layer, not a bank-side fraud detector and not a production risk model.

All rules are explicitly:
- `synthetic_test_only`;
- `bank_internal` scope;
- gated by `unverified_bank_internal_lawful_purpose_required`;
- disabled for cross-bank data;
- uncalibrated engineering thresholds, not fraud probabilities.

The rule catalogue is in `contracts/signal_detector_rules_v1.json`. Its required feature names follow the Notion 40 Signal Data Source, Legal Gate and Detector Matrix. It deliberately accepts only the declared feature names; raw account/card numbers, customer names, phone numbers, IP addresses, GPS coordinates, clipboard contents and arbitrary fields are rejected.

## Evaluation contract

For each signal:
1. Required feature values are checked against a versioned `all_of` rule.
2. Missing required features produce `INSUFFICIENT_DATA`, not a benign or suspicious verdict.
3. Failed conditions produce `NOT_DETECTED`.
4. A matched benign counter-indicator suppresses the candidate and records `SUPPRESSED_BENIGN`.
5. A fully matched rule produces a synthetic observation with a unique evidence ID, source, timestamp, evidence quality, recency, rule version and detector version.
6. All other detections are attached as corroboration references; the Risk Engine still independently enforces evidence uniqueness, signal-family caps and corroboration requirements.
7. Only the multi-signal Risk Engine calculates a 0–100 priority score. The detector itself does not decide guilt, block payments or issue bank actions.

## API

- `GET /api/prototype/detectors`: list the 40 rules, required feature names, status and legal gate.
- `POST /api/prototype/run`: provide `signal_features` with `synthetic: true`; the server evaluates the detector catalogue and feeds only generated observations to the existing pipeline.
- Precomputed `signal_events` or `signal_observations` cannot be mixed with `signal_features` in the same request.

## Test requirements

- Positive and negative synthetic feature path for every signal.
- Benign counter-evidence suppression for every rule with a benign condition.
- Missing-feature abstention.
- Unsupported identity/raw-data feature rejection.
- Timestamp, evidence quality and recency validation.
- End-to-end five-family synthetic scenario from feature bundle → 5 detectors → score 80 → Case eligibility. This is a deterministic software acceptance scenario, not measured fraud accuracy.

## Calibration and legal review still required

Thresholds, weights and feature windows are candidate engineering defaults. Before any real source-side use, each rule needs:
- bank data owner and approved lawful purpose;
- exact source schema and availability;
- completeness, freshness, provenance and quality measurement;
- benign and counter-evidence review;
- representative labelled data and independent validation;
- false-positive/false-negative and impact assessment;
- approved retention, access and sharing controls.

No real-bank connector or cross-bank data path is enabled by this release.

## External design references

- OWASP API Security Top 10 2023: https://owasp.org/API-Security/editions/2023/en/0x00-header/
- NIST SP 800-207 Zero Trust Architecture: https://csrc.nist.gov/pubs/sp/800/207/final
- Python SQLite transaction guidance: https://docs.python.org/3/library/sqlite3.html
- SQLite WAL concurrency limitations: https://www.sqlite.org/wal.html

These are engineering references only, not FINZANJIR regulatory approval.


## Detector-level Shadow Mode evaluation

The prototype also exposes:

- `POST /api/prototype/detector-shadow-evaluate`

Each scenario supplies `synthetic=true`, an expected synthetic QA label, a timezone-aware observation timestamp, a set of target signal IDs and a synthetic feature bundle. The endpoint runs the 40 candidate feature rules, converts detections into evidence-backed observations, and sends those observations through the multi-signal Risk Engine.

A key distinction is preserved: if any target signal lacks required feature fields, the scenario is reported as `abstained_insufficient_data`. Missing fields are not silently classified as benign. The response reports decisive coverage and abstention rate separately from TP/FP/TN/FN and precision/recall-style fixture metrics.

The metrics remain synthetic QA measurements only. They do not validate the availability, legality, completeness or predictive accuracy of any real bank source. The endpoint creates no Case, payment action, bank status change, customer block or authoritative decision.


## Source-event deduplication

The multi-signal scoring contract accepts an optional `event_key` in addition to `evidence_id`.

- `evidence_id` identifies the evidence record.
- `event_key` identifies the underlying source event or event group that produced the evidence.
- When multiple detector observations refer to the same `event_key`, they are grouped and only the strongest eligible contribution is scored.
- Evidence count and independent corroboration are based on distinct event keys, not merely distinct evidence record IDs.
- A signal cannot corroborate itself through another detector label attached to the same event key.
- One evidence ID cannot be reassigned to multiple event keys.
- If no event key is supplied, the evaluator defaults it to the evidence ID for backward compatibility.

This is a conservative duplicate-control mechanism. The bank-side adapter must supply event keys that reflect true source-event identity; a fabricated or overly broad event key can undercount independent evidence. Source event key design therefore remains a bank data-owner and legal-governance requirement.


## Temporal validity and freshness boundary

The v1 candidate contract now declares a zero lower bound for 13 fields that previously had only an upper bound: elapsed-time intervals, age values, geolocation accuracy, activity-time probability, session duration, graph-cycle duration and bank-verified name-match confidence. A negative value for a field with an explicit non-negative bound is treated as invalid input and returns `INSUFFICIENT_DATA` with reason `invalid_feature_values`; it is not converted into a benign non-detection or a suspicious signal.

Freshness is deliberately not inferred from the timestamp alone in v1:

- The scoring and detector interfaces validate that `observed_at` is a timezone-aware ISO-8601 timestamp.
- `recency_factor` is supplied by the source-side caller and constrained to [0, 1]. A value of 0 contributes zero priority points.
- The prototype does not calculate an age-based recency factor, define a universal maximum age, or account for source-specific clock skew.
- The API's default recency factor of 1.0 is a synthetic-demo default only. It is not an approved real-data freshness policy.
- Before any real source-side use, a bank data owner must define the event-time meaning, trusted reference clock, allowed clock skew, per-signal freshness window, and what happens when freshness cannot be established. Unknown or invalid freshness must abstain rather than assume fresh.

Arrival-order handling is also distinct from event chronology. Scoring is deterministic for the same set of event records regardless of the order in which they arrive. This does not validate a complete source-event sequence or prove that one event occurred before another. Sequence validation requires a versioned event-time contract with source identifiers, event timestamps, ingestion timestamps and ordering semantics.

Benign counter-evidence remains rule-specific through each detector's `benign_if` clauses. A general cross-signal contradiction-resolution model is not yet implemented; contradictory evidence must not be silently treated as resolved until that model and its source authority are specified.


## Feature type validation

The detector now checks each required feature's type against its declared comparison operator before evaluating a rule. A type mismatch (for example, the string "false" where a boolean is required, or the string "1" where a numeric interval is required) returns `INSUFFICIENT_DATA` with reason `invalid_feature_values`; it is not reported as a benign non-detection. The `ne` operator also returns false for mismatched types instead of treating a type mismatch as proof of inequality. This prevents malformed values from satisfying future negative-match rules.
