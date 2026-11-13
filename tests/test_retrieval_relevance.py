from finzanjir_ai.knowledge.index import build_knowledge_index
from finzanjir_ai.orchestration.engine import FINZANJIRAI


def _record(record_id, statement, aliases):
    return {
        "id": record_id,
        "concept_id": record_id,
        "canonical_concept_id": record_id,
        "statement": statement,
        "aliases": aliases,
        "evidence": {"status": "supported", "verification": "confirmed"},
        "provenance": [{"source": "synthetic-retrieval-fixture"}],
        "reconciliation": {},
    }


def test_identity_question_prefers_direct_project_concept_over_long_author_narrative():
    index = build_knowledge_index([
        _record(
            "ck-project-purpose",
            "FINZANJIR moliyaviy xavfsizlikni kuchaytirish, firibgarlik zanjirini tahlil qilish va fuqarolar mablag'ini himoya qilishga yordam beruvchi loyiha.",
            ["FINZANJIR nima", "moliyaviy xavfsizlik", "firibgarlik zanjiri tahlili"],
        ),
        _record(
            "ck-author-narrative",
            ("FINZANJIR kelajakdagi sun'iy ong va inson bilan muloqot haqida. " * 70),
            ["muallifning kelajak haqidagi qarashi"],
        ),
    ])

    result = FINZANJIRAI(index).answer(
        "FINZANJIR nima va u nima uchun kerak?",
        runtime_refs=(),
        working_memory_scope="identity-retrieval-test",
    )

    assert tuple(item.record_id for item in result.grounded_context.items) == ("ck-project-purpose",)
    assert result.answer.citations == ("ck-project-purpose",)
    assert result.answer.abstained is False


def test_generic_question_without_meaningful_terms_does_not_accept_arbitrary_records():
    index = build_knowledge_index([
        _record(
            "ck-unrelated",
            "Nima va qanday qilish kerakligi haqida umumiy izoh.",
            ["qanday izoh"],
        ),
    ])

    result = FINZANJIRAI(index).answer(
        "Nima?",
        runtime_refs=(),
        working_memory_scope="generic-query-test",
    )

    assert result.grounded_context.items == ()
    assert result.answer.abstained is True
    assert result.answer.citations == ()
