import asyncio
import json

import pytest

from finzanjir_ai.intel.worker_daemon import _load_sources, run_worker


def test_worker_daemon_requires_bounded_source_config():
    valid = [{
        "source_id": "cisa",
        "query": "public cybersecurity advisories",
        "allowed_domains": ["cisa.gov"],
        "enabled": False,
        "interval_minutes": 60,
    }]
    sources = _load_sources(json.dumps(valid))
    assert sources[0]["source_id"] == "cisa"
    invalid = [
        {},
        [],
        "not-json",
        [
            {"source_id": "x", "query": "q", "allowed_domains": ["a.gov"]},
            {"source_id": "x", "query": "q", "allowed_domains": ["b.gov"]},
        ],
        [{"source_id": "bad-interval", "query": "q", "allowed_domains": ["cisa.gov"], "interval_minutes": 5}],
        [{"source_id": "bad-enabled", "query": "q", "allowed_domains": ["cisa.gov"], "enabled": "false"}],
    ]
    for item in invalid:
        raw = item if isinstance(item, str) else json.dumps(item)
        with pytest.raises(RuntimeError):
            _load_sources(raw)


def test_worker_daemon_exits_cleanly_when_autonomy_is_disabled(monkeypatch):
    monkeypatch.delenv("FINZANJIR_AUTONOMOUS_RESEARCH_ENABLED", raising=False)
    asyncio.run(run_worker())


def test_worker_daemon_requires_separate_online_enable_switch(monkeypatch):
    monkeypatch.setenv("FINZANJIR_AUTONOMOUS_RESEARCH_ENABLED", "true")
    monkeypatch.delenv("FINZANJIR_AUTONOMOUS_RESEARCH_ONLINE_ENABLED", raising=False)
    with pytest.raises(RuntimeError, match="separately"):
        asyncio.run(run_worker())
