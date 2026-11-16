import asyncio
from datetime import datetime, timezone
import hashlib

from finzanjir_ai.intel.public_research_worker import build_public_research_worker
from finzanjir_ai.intel.runtime_store import LocalResearchRuntimeStore


class FakeSearch:
    def __init__(self, results):
        self.results = results
        self.calls = []

    def search(self, query, *, max_results=5, include_raw_content=False):
        self.calls.append((query, max_results, include_raw_content))
        return {"results": self.results}


def make_store(tmp_path):
    store = LocalResearchRuntimeStore(tmp_path / "research.sqlite")
    store.register_job("job-1", "cisa", enabled=True, now=datetime.now(timezone.utc))
    return store


def test_worker_filters_domains_and_persists_quarantined_public_extract(tmp_path):
    store = make_store(tmp_path)
    search = FakeSearch([
        {
            "url": "https://www.cisa.gov/advisories/example",
            "title": "CISA Advisory",
            "raw_content": "Official public advisory text",
            "snippet": "short excerpt",
        },
        {
            "url": "https://evil.example/steal",
            "title": "Untrusted domain",
            "raw_content": "Do not accept",
        },
        {
            "url": "http://www.cisa.gov/insecure",
            "title": "HTTP source",
            "raw_content": "No",
        },
    ])
    worker = build_public_research_worker(
        source_id="cisa", query="public cybersecurity advisories",
        allowed_domains=["cisa.gov"], store=store, search_client=search,
    )
    result = asyncio.run(worker({}, 300))
    assert result.done is True
    assert result.items == 1
    assert search.calls == [("public cybersecurity advisories", 8, True)]
    digest = hashlib.sha256(b"Official public advisory text").hexdigest()
    candidate_id = hashlib.sha256(
        ("cisa" + "https://www.cisa.gov/advisories/example" + digest).encode()
    ).hexdigest()
    candidate = store.get_candidate(candidate_id)
    assert candidate is not None
    assert candidate.status == "quarantined"
    assert candidate.source_mode == "online"
    assert "Official public advisory text" in candidate.text
    assert "human source/licence review" in " ".join(
        ["External source extract is untrusted; human source/licence review required."]
    )


def test_worker_uses_snippet_when_provider_has_no_raw_content(tmp_path):
    store = make_store(tmp_path)
    worker = build_public_research_worker(
        source_id="nvd", query="public CVE advisories",
        allowed_domains=["nvd.nist.gov"], store=store,
        search_client=FakeSearch([{
            "url": "https://nvd.nist.gov/vuln/detail/CVE-2026-0001",
            "title": "CVE item", "snippet": "Public vulnerability summary",
        }]),
    )
    result = asyncio.run(worker({}, 300))
    assert result.items == 1
    assert result.bytes_processed == len("Public vulnerability summary")


def test_worker_skips_non_allowlisted_results_and_no_content(tmp_path):
    store = make_store(tmp_path)
    worker = build_public_research_worker(
        source_id="nvd", query="public CVE advisories",
        allowed_domains=["nvd.nist.gov"], store=store,
        search_client=FakeSearch([
            {"url": "https://other.example/page", "raw_content": "not allowed"},
            {"url": "https://nvd.nist.gov/empty", "raw_content": ""},
        ]),
    )
    result = asyncio.run(worker({}, 300))
    assert result.done is True
    assert result.items == 0


def test_worker_requires_exact_domain_configuration(tmp_path):
    store = make_store(tmp_path)
    for domains in ([], ["https://cisa.gov"], ["cisa.gov/path"], ["cisa.gov:443"]):
        try:
            build_public_research_worker(
                source_id="cisa", query="advisory", allowed_domains=domains,
                store=store, search_client=FakeSearch([]),
            )
        except ValueError:
            continue
        raise AssertionError(f"unsafe domain config was accepted: {domains}")


def test_supervisor_executes_real_research_handler_and_audits_quarantine(tmp_path):
    from finzanjir_ai.intel.cycle_supervisor import AutonomousCycleSupervisor, WorkCyclePolicy

    store = make_store(tmp_path)
    worker = build_public_research_worker(
        source_id="cisa", query="public CISA advisories",
        allowed_domains=["cisa.gov"], store=store,
        search_client=FakeSearch([{
            "url": "https://www.cisa.gov/advisories/test",
            "title": "CISA test advisory",
            "raw_content": "Public advisory evidence.",
        }]),
    )
    supervisor = AutonomousCycleSupervisor(
        store, WorkCyclePolicy(work_seconds=10, rest_minutes=10, lease_seconds=60)
    )
    result = asyncio.run(supervisor.run_cycle("job-1", worker))
    assert result["status"] == "completed"
    assert result["items"] == 1
    assert store.audit_events("job-1")[0]["status"] == "completed"
    assert store.get_candidate(
        hashlib.sha256(
            ("cisa" + "https://www.cisa.gov/advisories/test" +
             hashlib.sha256(b"Public advisory evidence.").hexdigest()).encode()
        ).hexdigest()
    ) is not None
