from __future__ import annotations

from typing import Any

from finzanjir_ai.knowledge.index import KnowledgeIndex

from .flow import build_system_flow


def run_full_demo(transaction: dict[str, Any], *, knowledge_index: KnowledgeIndex) -> dict[str, Any]:
    """Run the same executable flow used by the unified prototype windows."""
    return build_system_flow().execute(transaction, knowledge_index=knowledge_index)
