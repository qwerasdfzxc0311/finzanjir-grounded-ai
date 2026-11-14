from finzanjir_ai.retrieval.text import (
    cyrillic_to_latin_search_variant,
    query_script_variants,
)


def test_uzbek_cyrillic_query_gets_latin_search_variant():
    assert cyrillic_to_latin_search_variant("Фуқаролар маблағини ҳимоя қилиш") == (
        "fuqarolar mablag'ini himoya qilish"
    )


def test_kazakh_and_karakalpak_specific_letters_are_normalized_for_search():
    assert cyrillic_to_latin_search_variant("Қаржы және қауіпсіздік") == "qarjy zhane qauipsizdik"
    assert cyrillic_to_latin_search_variant("Қарақалпақ") == "qaraqalpaq"


def test_russian_cyrillic_is_not_transliterated_as_a_central_asian_variant():
    assert cyrillic_to_latin_search_variant("Что такое FINZANJIR?") is None


def test_script_variants_keep_original_query_first_and_do_not_duplicate():
    assert query_script_variants("ФИНЗАНЖИР ҳаққында") == (
        "ФИНЗАНЖИР ҳаққында",
        "finzanjir haqqinda",
    )
    assert query_script_variants("FINZANJIR nima?") == ("FINZANJIR nima?",)
