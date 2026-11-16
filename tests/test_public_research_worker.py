import asyncio
from datetime import datetime, timezone

from finzanjir_ai.intel.public_research_worker import build_public_research_worker
from finzanjir_ai.intel.runtime_store import LocalResearchRuntimeStore


class FakeSearch:
    def __init__(self, results):
        self.results = results
        self.calls = []

    def search(self, query, *, max_results=5):
        self.calls.append((query, max_results))
        return {"results": self.results}


class FakeFetch:
    def __init__(self):
        self.calls = []

    def fetch(self, url):
        self.calls.append(url)
        return type("Evidence", (), {
            "text": "Official public advisory text",
            "url": url,
            "content_type": "text/html",
        })()


def make_store(tmp_path):
    store = LocalResearchRuntimeStore(tmp_path / "research.sqlite")
    store.register_job("job-1", "cisa", enabled=True, now=datetime.now(timezone.utc))
    return store


def test_worker_filters_domains_and_persists_source_in_quarantine(tmp_path):
    store = make_store(tmp_path)
    search = FakeSearch([
        {"url": "https://www.cisa.gov/advisories/example", "title": "CISA Advisory"},
        {"url": "https://evil.example/steal", "title": "Untrusted domain"},
        {"url": "http://www.cisa.gov/insecure", "title": "HTTP source"},
    ])
    fetch = FakeFetch()
    worker = build_public_research_worker(
        source_id="cisa", query="public cybersecurity advisories",
        allowed_domains=["cisa.gov"], store=store,
        search_client=search, fetch_client=fetch,
    )
    first = asyncio.run(worker({}, 300))
    assert first.done is False
    assert len(first.checkpoint["results"]) == 1
    second = asyncio.run(worker(first.checkpoint, 300))
    assert second.done is True
    assert second.items == 1
    assert fetch.calls == ["https://www.cisa.gov/advisories/example"]
    candidate = store.get_candidate(
        __import__("hashlib").sha256(
            ("cisa" + "https://www.cisa.gov/advisories/example" +
             __import__("hashlib").sha256(b"Official public advisory text").hexdigest()).encode()
        ).hexdigest()
    )
    assert candidate is not None
    assert candidate.status == "quarantined"
    assert candidate.source_mode == "online"
    assert "Official public advisory text" in candidate.text


def test_worker_returns_done_when_search_has_no_allowlisted_results(tmp_path):
    store = make_store(tmp_path)
    worker = build_public_research_worker(
        source_id="nvd", query="public CVE advisories",
        allowed_domains=["nvd.nist.gov"], store=store,
        search_client=FakeSearch([{"url": "https://other.example/page", "title": "No"}]),
        fetch_client=FakeFetch(),
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
                store=store, search_client=FakeSearch([]), fetch_client=FakeFetch(),
            )
        except ValueError:
            continue
        raise AssertionError(f"unsafe domain config was accepted: {domains}")
