from finzanjir_ai.language.morphology import morphological_stem


def test_common_uzbek_inflections_share_a_conservative_stem():
    assert morphological_stem("fuqarolarning") == "fuqaro"
    assert morphological_stem("mablag'larini") == "mablag"
    assert morphological_stem("kartasini") == "karta"


def test_kazakh_and_russian_suffixes_are_normalized_without_one_letter_stripping():
    assert morphological_stem("картаны") == "карта"
    assert morphological_stem("қаржылық") == "қаржы"
    assert morphological_stem("банков") == "банк"
    assert morphological_stem("карта") == "карта"


def test_unknown_or_short_tokens_are_preserved():
    assert morphological_stem("risk") == "risk"
    assert morphological_stem("AI") == "ai"
