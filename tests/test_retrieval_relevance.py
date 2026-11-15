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



def test_project_question_excludes_legacy_author_record_using_entity_and_provenance():
    author_record = {
        "id": "ck-legacy-author",
        "concept_id": "author-motivation",
        "canonical_concept_id": "author-motivation",
        "entity_id": "person:salamat_smaylov",
        "facet": "project_motivation",
        "statement": "Muallif oilaviy moliyaviy yo'qotishlar sabab FINZANJIR g'oyasini boshlagan.",
        "aliases": ["fuqarolar mablag'ini himoya qilish", "muallif motivatsiyasi"],
        "evidence": {"status": "supported", "verification": "confirmed"},
        "provenance": [{
            "source_type": "project_archive_document",
            "source_sections": ["Loyiha muallifining motivatsiyasi"],
        }],
        "reconciliation": {},
    }
    project_record = _record(
        "ck-project-protection",
        "FINZANJIR fuqarolarning qonuniy mablag'lari va tranzaksiyalariga asossiz zarar yetmasligiga yordam beradi.",
        ["fuqarolar mablag'ini himoya qilish", "qonuniy tranzaksiyalar"],
    )
    result = FINZANJIRAI(build_knowledge_index([author_record, project_record])).answer(
        "FINZANJIR fuqarolar pulini qanday himoya qiladi?",
        runtime_refs=(),
        working_memory_scope="legacy-author-provenance-isolation",
    )
    refs = tuple(item.record_id for item in result.grounded_context.items)
    assert "ck-legacy-author" not in refs
    assert "ck-project-protection" in refs


def _domain_record(record_id, statement, aliases, domain, source_files=(), title="synthetic_project_source"):
    return {
        "id": record_id,
        "concept_id": record_id,
        "canonical_concept_id": record_id,
        "domain": domain,
        "title": title,
        "statement": statement,
        "aliases": aliases,
        "evidence": {"status": "supported", "verification": "confirmed"},
        "provenance": [{"source_files": list(source_files)}],
        "reconciliation": {},
    }


def test_project_question_excludes_general_biology_record_even_with_exact_query_alias():
    query = "FINZANJIR boshqa елдерден несімен ерекшеленеді?"
    biology = _domain_record(
        "ck_001693",
        "Жасуша — тірі ағзалардың негізгі құрылымдық және функционалдық бірлігі. "
        "Әртүрлі ағзаларда жасушалар құрылысы мен қызметі бойынша ерекшеленеді.",
        [query],
        "biology",
        ("knowledge/specific_learning_cards.json",),
    )
    index = build_knowledge_index([biology])

    result = FINZANJIRAI(index).answer(
        query,
        runtime_refs=(),
        working_memory_scope="project-domain-isolation",
    )

    assert result.grounded_context.items == ()
    assert result.answer.abstained is True
    assert result.answer.citations == ()


def test_project_question_keeps_finZanjir_project_domain_and_project_source_unclassified_records():
    query = "FINZANJIR boshqa davlatlardan farqi nimada?"
    project = _domain_record(
        "ck-project-purpose",
        "FINZANJIR moliyaviy firibgarlik xavflarini aniqlash va tahlil qilishga yo'naltirilgan loyiha.",
        [query, "FINZANJIR moliyaviy xavfsizlik"],
        "finzanjir_project",
        ("Finzanjir konsepsiyasi va qoshimsha malumotlar hujjatlar/FINZANJIR_KONSEPSIYA_V14.pdf",),
    )
    unclassified_project = _domain_record(
        "ck-project-legacy",
        "FINZANJIR fuqarolarning qonuniy mablag'larini himoya qilishga qaratilgan loyiha.",
        ["fuqarolar mablag'ini himoya qilish", query],
        "unclassified",
        ("FINZANJIR_KONSEPSIYA_FINAL.html",),
    )
    biology = _domain_record(
        "ck-unrelated-biology",
        "Жасуша — тірі ағзалардың негізгі құрылымдық бірлігі.",
        [query],
        "biology",
        ("knowledge/specific_learning_cards.json",),
    )
    query_alias = _domain_record(
        "ck-finzanjir-query-alias",
        "FINZANJIR",
        [query],
        "finzanjir",
        ("knowledge/multilingual_query_patterns.json",),
        title="multilingual_query_pattern",
    )
    result = FINZANJIRAI(build_knowledge_index([biology, project, unclassified_project, query_alias])).answer(
        query,
        runtime_refs=(),
        working_memory_scope="project-domain-allowlist",
    )

    refs = {item.record_id for item in result.grounded_context.items}
    assert "ck-project-purpose" in refs
    assert "ck-project-legacy" in refs
    assert "ck-unrelated-biology" not in refs
    assert "ck-finzanjir-query-alias" not in refs
    assert result.answer.abstained is False
