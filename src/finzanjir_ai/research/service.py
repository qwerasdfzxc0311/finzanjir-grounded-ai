from __future__ import annotations

from typing import Any

import httpx

from finzanjir_ai.research.local_answer import compose_tavily_local_answer
from finzanjir_ai.research.resilience import PublicResearchCache, ProviderCooldown
from finzanjir_ai.research.tavily import TavilySearchClient
from finzanjir_ai.research.wikipedia import WikimediaSearchClient


_PUBLIC_RESEARCH_CACHE = PublicResearchCache(ttl_seconds=6 * 60 * 60, max_entries=128)
_TAVILY_COOLDOWN = ProviderCooldown()


def _failure_status(exc: Exception) -> str:
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        if code == 429:
            return "rate_limited"
        if code == 402:
            return "quota_exhausted"
        if code in (401, 403):
            return "authentication_or_permission_failed"
        if code >= 500:
            return "provider_unavailable"
        return "request_rejected"
    if isinstance(exc, httpx.HTTPError):
        return "network_error"
    return "provider_unavailable"


def _payload(
    question: str,
    research: dict[str, Any],
    *,
    runtime_refs: list[str],
    source_provider: str,
    research_provider: str,
    diagnostics: list[dict[str, Any]],
    explicit_search: bool,
) -> dict[str, Any]:
    composed = compose_tavily_local_answer(
        question,
        research.get("results", []),
        max_sentences=5,
        max_sources=6,
        provider_name=source_provider,
    )
    generation_mode = "web_search" if explicit_search else composed.generation_mode
    if research_provider == "cache" and not explicit_search and not composed.abstained:
        generation_mode = "cached_local_extractive"
    return {
        "answer": composed.answer,
        "confidence": composed.confidence,
        "abstained": composed.abstained,
        "generation_mode": generation_mode,
        "composition_mode": composed.generation_mode,
        "confidence_basis": composed.confidence_basis,
        "provider_status": "not_attempted",
        "provider_diagnostics": [],
        "research_provider": research_provider,
        "research_diagnostics": diagnostics,
        "knowledge_refs": [],
        "provenance": list(composed.provenance),
        "runtime_refs": list(runtime_refs),
        "external_sources": list(composed.sources),
        "research_status": "completed" if not composed.abstained else "insufficient_extractable_evidence",
    }


def search_and_compose(
    question: str,
    *,
    runtime_refs: list[str] | None = None,
    explicit_search: bool = False,
) -> dict[str, Any] | None:
    """Search cache, Tavily and then Wikimedia; answer composition stays local."""
    refs = list(runtime_refs or [])
    diagnostics: list[dict[str, Any]] = []

    cached = _PUBLIC_RESEARCH_CACHE.get(question)
    if cached:
        payload = _payload(
            question,
            {"results": cached.get("results", [])},
            runtime_refs=refs,
            source_provider=str(cached.get("provider") or "Tavily"),
            research_provider="cache",
            diagnostics=diagnostics,
            explicit_search=explicit_search,
        )
        if not payload["abstained"]:
            return payload

    candidates: list[dict[str, Any]] = []
    if _TAVILY_COOLDOWN.is_open():
        diagnostics.append({
            "provider": "tavily",
            "status": _TAVILY_COOLDOWN.status(),
            "cooldown_seconds": _TAVILY_COOLDOWN.remaining_seconds(),
        })
    else:
        try:
            research = TavilySearchClient().search(
                question,
                max_results=6,
                search_depth="advanced",
                include_raw_content=True,
            )
            _TAVILY_COOLDOWN.record_success()
            payload = _payload(
                question,
                research,
                runtime_refs=refs,
                source_provider="Tavily",
                research_provider="tavily",
                diagnostics=diagnostics,
                explicit_search=explicit_search,
            )
            if not payload["abstained"]:
                _PUBLIC_RESEARCH_CACHE.put(question, "Tavily", research.get("results", []))
                return payload
            if research.get("results"):
                candidates.append(payload)
            diagnostics.append({"provider": "tavily", "status": "insufficient_extractable_evidence"})
        except ValueError:
            raise
        except RuntimeError:
            diagnostics.append({"provider": "tavily", "status": "not_configured"})
        except (httpx.HTTPError, OSError) as exc:
            status = _failure_status(exc)
            cooldown = _TAVILY_COOLDOWN.record_failure(status)
            diagnostics.append({
                "provider": "tavily",
                "status": status,
                "cooldown_seconds": cooldown,
            })

    try:
        backup = WikimediaSearchClient().search(question, max_results=6)
        backup_results = backup.get("results", [])
        if backup_results:
            payload = _payload(
                question,
                backup,
                runtime_refs=refs,
                source_provider="Wikimedia",
                research_provider="wikimedia",
                diagnostics=diagnostics,
                explicit_search=explicit_search,
            )
            if not payload["abstained"]:
                _PUBLIC_RESEARCH_CACHE.put(question, "Wikimedia", backup_results)
                return payload
            candidates.append(payload)
            diagnostics.append({"provider": "wikimedia", "status": "insufficient_extractable_evidence"})
        else:
            diagnostics.append({
                "provider": "wikimedia",
                "status": backup.get("status", "no_results"),
            })
    except ValueError:
        raise
    except (httpx.HTTPError, OSError):
        diagnostics.append({"provider": "wikimedia", "status": "network_error"})

    if candidates:
        best = max(candidates, key=lambda item: len(item.get("external_sources", [])))
        best["research_diagnostics"] = diagnostics
        return best
    return None


def clear_research_state_for_tests() -> None:
    _PUBLIC_RESEARCH_CACHE.clear()
    _TAVILY_COOLDOWN.record_success()
