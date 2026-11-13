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



def test_project_questions_never_retrieve_author_biography_as_project_evidence():
    index = build_knowledge_index([
        _record(
            "project_0002",
            "FINZANJIR fuqarolarning pul oqimlarini tahlil qilib, qonuniy mablag'larini firibgarlik xavfidan himoya qilishga yordam beradi.",
            ["fuqarolar pulini himoya qilish", "moliyaviy xavfsizlik"],
        ),
        _record(
            "author_0004",
            "Muallif FINZANJIR g'oyasini oilaviy yo'qotishlar va fuqarolar mablag'ini himoya qilish istagi sabab boshlagan.",
            ["muallif motivatsiyasi", "loyiha yaratilish sababi"],
        ),
    ])

    result = FINZANJIRAI(index).answer(
        "FINZANJIR fuqarolar pulini qanday himoya qiladi?",
        runtime_refs=(),
        working_memory_scope="project-author-layer-isolation",
    )

    refs = tuple(item.record_id for item in result.grounded_context.items)
    assert "author_0004" not in refs
    assert "project_0002" in refs
    assert result.answer.citations
    assert "author_0004" not in result.answer.citations
