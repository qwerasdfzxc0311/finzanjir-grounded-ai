import asyncio
import json

import pytest

from finzanjir_ai.intel.worker_daemon import _load_sources, run_worker


def test_worker_daemon_requires_bounded_source_config():
    sources = _load_sources(json.dumps([{
        "source_id": "cisa",
        "query": "public cybersecurity advisories",
        "allowed_domains": ["cisa.gov"],
        "enabled": False,
    }]))
    assert sources[0]["source_id"] == "cisa"
    for raw in ("{}", "[]", "not-json", json.dumps([
        {"source_id": "x", "query": "q", "allowed_domains": ["a.gov"]},
        {"source_id": "x", "query": "q", "allowed_domains": ["b.gov"]},
    ])):
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
