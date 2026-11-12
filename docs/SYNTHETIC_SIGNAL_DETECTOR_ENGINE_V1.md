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
