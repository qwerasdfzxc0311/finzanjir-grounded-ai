"""Opt-in process entrypoint for FINZANJIR's autonomous public research worker.

Nothing runs unless the operator explicitly enables both switches and supplies
persistent storage, a Tavily key, and a JSON source/domain allowlist.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
from pathlib import Path
from typing import Any

from .cycle_supervisor import AutonomousCycleSupervisor, WorkCyclePolicy
from .public_research_worker import build_public_research_worker
from .runtime_store import LocalResearchRuntimeStore


logger = logging.getLogger("finzanjir.autonomous_worker")


def _truthy(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _load_sources(raw: str) -> list[dict[str, Any]]:
    try:
        sources = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("FINZANJIR_RESEARCH_SOURCES_JSON is not valid JSON") from exc
    if not isinstance(sources, list) or not sources:
        raise RuntimeError("At least one public research source must be configured")
    if len(sources) > 20:
        raise RuntimeError("At most 20 public research sources may be configured")
    seen = set()
    for item in sources:
        if not isinstance(item, dict):
            raise RuntimeError("Each research source must be an object")
        source_id = str(item.get("source_id") or "").strip()
        query = str(item.get("query") or "").strip()
        domains = item.get("allowed_domains")
        if not source_id or len(source_id) > 80 or source_id in seen:
            raise RuntimeError("Research source IDs must be unique and 1-80 characters")
        if not query or len(query) > 500:
            raise RuntimeError("Each research source requires a 1-500 character query")
        if not isinstance(domains, list) or not domains or not all(isinstance(domain, str) for domain in domains):
            raise RuntimeError("Each research source requires an explicit string domain allowlist")
        if not isinstance(item.get("enabled", False), bool):
            raise RuntimeError("Research source enabled flag must be a boolean")
        try:
            interval = int(item.get("interval_minutes", 60))
        except (TypeError, ValueError) as exc:
            raise RuntimeError("Research source interval must be an integer") from exc
        if interval < 60 or interval > 10080:
            raise RuntimeError("Research source interval must be between 60 and 10080 minutes")
        seen.add(source_id)
    return sources


async def run_worker() -> None:
    if not _truthy("FINZANJIR_AUTONOMOUS_RESEARCH_ENABLED"):
        logger.warning("Autonomous research is disabled; worker process will exit.")
        return
    if not _truthy("FINZANJIR_AUTONOMOUS_RESEARCH_ONLINE_ENABLED"):
        raise RuntimeError("Online autonomous research must be explicitly enabled separately")
    if not os.getenv("TAVILY_API_KEY"):
        raise RuntimeError("TAVILY_API_KEY is required for online autonomous research")

    db_path = os.getenv("FINZANJIR_RESEARCH_DB_PATH", "").strip()
    if not db_path or not Path(db_path).is_absolute():
        raise RuntimeError("FINZANJIR_RESEARCH_DB_PATH must be an absolute persistent-disk path")
    raw_sources = os.getenv("FINZANJIR_RESEARCH_SOURCES_JSON", "")
    sources = _load_sources(raw_sources)
    store = LocalResearchRuntimeStore(db_path)

    handlers = {}
    for source in sources:
        source_id = str(source["source_id"])
        job_id = "public-research-" + source_id
        interval = int(source.get("interval_minutes", 60))
        store.register_job(job_id, source_id, interval_minutes=max(60, interval), enabled=False)
        enabled = bool(source.get("enabled", False))
        if enabled:
            store.set_enabled(job_id, True)
        else:
            store.set_enabled(job_id, False)
        handlers[source_id] = build_public_research_worker(
            source_id=source_id,
            query=str(source["query"]),
            allowed_domains=source["allowed_domains"],
            store=store,
        )

    policy = WorkCyclePolicy(
        work_seconds=3600,
        rest_minutes=10,
        lease_seconds=300,
        poll_seconds=5,
        max_steps_per_cycle=500,
    )
    supervisor = AutonomousCycleSupervisor(store, policy)
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_event.set)
        except NotImplementedError:
            pass
    logger.info("Autonomous research worker started with %d configured source(s).", len(handlers))
    await supervisor.run_forever(handlers, stop_event)
    logger.info("Autonomous research worker stopped cleanly.")


def main() -> None:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
