from finzanjir_ai.answer.providers import LLMGateway


def test_gateway_is_disabled_without_server_keys():
    gateway = LLMGateway(environ={})
    assert gateway.configured_providers() == ()
    assert gateway.generate_json(system="system", prompt="prompt") is None


def test_gateway_prefers_gemini_and_keeps_openrouter_as_fallback():
    gateway = LLMGateway(environ={
        "GEMINI_API_KEY": "not-a-real-test-secret",
        "OPENROUTER_API_KEY": "not-a-real-test-secret",
    })
    assert gateway.configured_providers() == ("gemini", "openrouter")


def test_gateway_can_be_configured_to_use_openrouter_only():
    gateway = LLMGateway(environ={
        "FINZANJIR_LLM_PROVIDER": "openrouter",
        "GEMINI_API_KEY": "not-a-real-test-secret",
        "OPENROUTER_API_KEY": "not-a-real-test-secret",
    })
    assert gateway.configured_providers() == ("openrouter",)


def test_json_parser_accepts_plain_and_fenced_json():
    assert LLMGateway._parse_json('{"search_queries":["firibgarlik zanjiri"]}') == {
        "search_queries": ["firibgarlik zanjiri"]
    }
    fenced = chr(96) * 3 + 'json\\n{"ok":true}\\n' + chr(96) * 3
    assert LLMGateway._parse_json(fenced) == {"ok": True}


def test_query_expansion_filters_empty_and_original_question(monkeypatch):
    gateway = LLMGateway(environ={})
    monkeypatch.setattr(
        gateway,
        "generate_json",
        lambda **kwargs: {"search_queries": ["  ", "pulni himoyalash", "SAVOL", "pulni himoyalash"]},
    )
    assert gateway.expand_question("SAVOL") == ("pulni himoyalash",)
