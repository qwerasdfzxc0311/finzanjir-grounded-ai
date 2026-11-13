import pytest

from finzanjir_ai.evidence.provenance import SyntheticEvidenceProvenanceChain


def _append(chain, evidence_id="evidence-1", event_id="event-1", payload_digest="a" * 64):
    return chain.append(
        evidence_id=evidence_id,
        event_id=event_id,
        source="synthetic-source",
        observed_at="2026-11-13T09:00:00Z",
        acquisition_method="synthetic_fixture",
        source_version="source-schema-v1",
        payload_digest=payload_digest,
    )


def test_synthetic_provenance_chain_links_records_and_verifies_in_order():
    chain = SyntheticEvidenceProvenanceChain()
    first = _append(chain)
    second = _append(chain, evidence_id="evidence-2", event_id="event-2", payload_digest="b" * 64)

    report = chain.verify()

    assert first["sequence"] == 1
    assert first["previous_record_hash"] is None
    assert second["sequence"] == 2
    assert second["previous_record_hash"] == first["record_hash"]
    assert report["valid"] is True
    assert report["record_count"] == 2
    assert report["errors"] == []
    assert report["signature_verified"] is False
    assert report["source_authenticated"] is False
    assert report["payload_digest_verified"] is False
    assert report["opaque_ids_semantically_verified"] is False
    assert report["durable"] is False
    assert report["truthfulness_proven"] is False


def test_provenance_verifier_detects_metadata_tampering_and_broken_chain():
    chain = SyntheticEvidenceProvenanceChain()
    _append(chain)
    _append(chain, evidence_id="evidence-2", event_id="event-2")
    records = [dict(item) for item in chain.records()]
    records[0]["source"] = "tampered-source"
    records[1]["previous_record_hash"] = "0" * 64

    report = chain.verify(records)

    assert report["valid"] is False
    assert {item["reason"] for item in report["errors"]} >= {
        "record_hash_mismatch",
        "previous_hash_mismatch",
    }


def test_provenance_chain_rejects_duplicate_evidence_and_non_synthetic_scope():
    chain = SyntheticEvidenceProvenanceChain()
    _append(chain)
    with pytest.raises(ValueError, match="duplicate evidence_id"):
        _append(chain, evidence_id="evidence-1", event_id="event-2")

    with pytest.raises(ValueError, match="synthetic data only"):
        chain.append(
            evidence_id="evidence-2",
            event_id="event-2",
            source="source",
            observed_at="2026-11-13T09:00:00Z",
            acquisition_method="fixture",
            source_version="v1",
            payload_digest="c" * 64,
            data_mode="bank",
        )


def test_provenance_chain_requires_timezone_and_sha256_payload_digest():
    chain = SyntheticEvidenceProvenanceChain()
    with pytest.raises(ValueError, match="timezone"):
        chain.append(
            evidence_id="evidence-1",
            event_id="event-1",
            source="source",
            observed_at="2026-11-13T09:00:00",
            acquisition_method="fixture",
            source_version="v1",
            payload_digest="a" * 64,
        )

    with pytest.raises(ValueError, match="SHA-256"):
        chain.append(
            evidence_id="evidence-1",
            event_id="event-1",
            source="source",
            observed_at="2026-11-13T09:00:00Z",
            acquisition_method="fixture",
            source_version="v1",
            payload_digest="not-a-digest",
        )


def test_provenance_records_are_returned_as_detached_copies():
    chain = SyntheticEvidenceProvenanceChain()
    _append(chain)
    records = chain.records()
    records[0]["source"] = "mutated-copy"

    assert chain.records()[0]["source"] == "synthetic-source"
    assert chain.verify()["valid"] is True



def test_provenance_verifier_rejects_unexpected_fields_and_invalid_hash_shape():
    chain = SyntheticEvidenceProvenanceChain()
    _append(chain)
    records = [dict(item) for item in chain.records()]
    records[0]["raw_account_number"] = "not-allowed"
    records[0]["record_hash"] = "not-a-hash"

    report = chain.verify(records)

    reasons = {item["reason"] for item in report["errors"]}
    assert "unexpected_fields" in reasons
    assert "invalid_record_hash" in reasons
