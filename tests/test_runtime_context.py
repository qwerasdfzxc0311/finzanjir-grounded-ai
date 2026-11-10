import pytest

from finzanjir_ai.runtime.context import RuntimeContext


def test_runtime_context_keeps_runtime_refs_separate_from_authoritative_knowledge():
    context = RuntimeContext.from_refs(
        knowledge_refs=("ck-1",),
        runtime_refs=("tx-1", "sig-1"),
        working_memory_scope="case-1",
    )

    assert context.knowledge_refs == ("ck-1",)
    assert context.runtime_refs == ("tx-1", "sig-1")
    assert context.working_memory_scope == "case-1"
    assert context.can_write_authoritative_knowledge is False


def test_runtime_context_rejects_missing_scope():
    with pytest.raises(ValueError, match="working_memory_scope"):
        RuntimeContext.from_refs(knowledge_refs=(), runtime_refs=(), working_memory_scope="")
