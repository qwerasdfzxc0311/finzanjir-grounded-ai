from finzanjir_ai.retrieval.cross_lingual import (
    cross_lingual_query_variants,
    translate_search_hint,
)


def test_russian_comparison_query_gets_low_priority_uzbek_hint():
    query = "Чем FINZANJIR отличается от похожих систем в Узбекистане и других странах?"
    hint, mapped = translate_search_hint(query, "ru")
    assert mapped >= 3
    assert hint is not None
    assert "farq" in hint
    assert "o'xshash" in hint
    assert "tizim" in hint


def test_english_comparison_query_gets_low_priority_uzbek_hint():
    query = "How is FINZANJIR different from similar fraud-prevention systems in other countries?"
    hint, mapped = translate_search_hint(query, "en")
    assert mapped >= 3
    assert hint is not None
    assert "farq" in hint
    assert "o'xshash" in hint
    assert "firibgarlik" in hint
    assert "tizim" in hint


def test_kazakh_and_karakalpak_queries_get_domain_hints():
    kazakh = "FINZANJIR басқа елдердегі ұқсас жүйелерден несімен ерекшеленеді?"
    kk_hint, kk_count = translate_search_hint(kazakh, "kk")
    assert kk_count >= 3
    assert kk_hint is not None
    assert "o'xshash" in kk_hint
    assert "farq" in kk_hint
    karakalpak = "FINZANJIR basqa mámleketlerdegi usas joybarlardan neshe menen parıqlanadı?"
    kaa_hint, kaa_count = translate_search_hint(karakalpak, "kaa")
    assert kaa_count >= 3
    assert kaa_hint is not None
    assert "o'xshash" in kaa_hint
    assert "farq" in kaa_hint
    assert "loyiha" in kaa_hint


def test_query_bridge_preserves_original_query_as_first_variant():
    query = "Чем FINZANJIR отличается от похожих систем?"
    variants = cross_lingual_query_variants(query)
    assert variants[0] == query
    assert len(variants) >= 2


def test_uzbek_query_does_not_receive_unneeded_translation_hint():
    query = "FINZANJIRning arxitekturasi qanday?"
    hint, mapped = translate_search_hint(query, "uz")
    assert hint is None
    assert mapped == 0
