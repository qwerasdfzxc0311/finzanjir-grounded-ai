import httpx

from finzanjir_ai.answer.providers import LLMGateway


def test_gateway_is_disabled_without_server_keys():
    gateway = LLMGateway(environ={})
    assert gateway.configured_providers() == ()
    assert gateway.generate_json(system="system", prompt="prompt") is None
    assert gateway.last_status == "not_configured"


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
    fenced = chr(96) * 3 + "json" + chr(10) + '{"ok":true}' + chr(10) + chr(96) * 3
    assert LLMGateway._parse_json(fenced) == {"ok": True}


def test_query_expansion_filters_empty_and_original_question(monkeypatch):
    gateway = LLMGateway(environ={})
    monkeypatch.setattr(
        gateway,
        "generate_json",
        lambda **kwargs: {"search_queries": ["  ", "pulni himoyalash", "SAVOL", "pulni himoyalash"]},
    )
    assert gateway.expand_question("SAVOL") == ("pulni himoyalash",)


def test_gateway_keeps_common_personal_and_payment_identifiers_out_of_provider_calls():
    assert not LLMGateway.can_send_text("Karta raqami 8600 1234 5678 9012")
    assert not LLMGateway.can_send_text("Telefon +998 90 123 45 67")
    assert not LLMGateway.can_send_text("Email user@example.com")
    assert not LLMGateway.can_send_text("Telefon +7 999 123-45-67")
    assert not LLMGateway.can_send_text("Pasport AA1234567")
    assert not LLMGateway.can_send_text("IBAN GB82 WEST 1234 5698 7654 32")
    assert LLMGateway.can_send_text("FINZANJIR firibgarlik zanjirini qanday aniqlaydi?")



def test_gateway_reports_provider_failure_without_exposing_provider_details(monkeypatch):
    gateway = LLMGateway(environ={"GEMINI_API_KEY": "not-a-real-test-secret"})

    def fail_request(*_args, **_kwargs):
        raise httpx.ConnectError("synthetic provider outage")

    monkeypatch.setattr(gateway, "_generate_with", fail_request)
    assert gateway.generate_json(system="system", prompt="prompt") is None
    assert gateway.last_status == "provider_failed"



def test_gateway_reports_safe_auth_failure_category(monkeypatch):
    gateway = LLMGateway(environ={"GEMINI_API_KEY": "not-a-real-test-secret"})
    request = httpx.Request("POST", "https://example.invalid")
    response = httpx.Response(401, request=request)

    def fail_request(*_args, **_kwargs):
        raise httpx.HTTPStatusError("secret-bearing provider body must not leak", request=request, response=response)

    monkeypatch.setattr(gateway, "_generate_with", fail_request)
    assert gateway.generate_json(system="system", prompt="prompt") is None
    assert gateway.last_status == "provider_failed"
    assert gateway.last_provider_failures == [
        {"provider": "gemini", "status": "authentication_or_permission_failed"}
    ]
    assert "secret-bearing" not in repr(gateway.last_provider_failures)


def test_gateway_reports_rate_limit_category(monkeypatch):
    gateway = LLMGateway(environ={"OPENROUTER_API_KEY": "not-a-real-test-secret"})
    request = httpx.Request("POST", "https://example.invalid")
    response = httpx.Response(429, request=request)

    def fail_request(*_args, **_kwargs):
        raise httpx.HTTPStatusError("rate limit", request=request, response=response)

    monkeypatch.setattr(gateway, "_generate_with", fail_request)
    assert gateway.generate_json(system="system", prompt="prompt") is None
    assert gateway.last_provider_failures == [
        {"provider": "openrouter", "status": "rate_limited"}
    ]


def test_gateway_reports_timeout_category(monkeypatch):
    gateway = LLMGateway(environ={"GEMINI_API_KEY": "not-a-real-test-secret"})

    def fail_request(*_args, **_kwargs):
        raise httpx.ReadTimeout("private transport details")

    monkeypatch.setattr(gateway, "_generate_with", fail_request)
    assert gateway.generate_json(system="system", prompt="prompt") is None
    assert gateway.last_provider_failures == [
        {"provider": "gemini", "status": "timeout"}
    ]

def test_gateway_logs_only_sanitized_provider_failure_category(caplog, monkeypatch):
    gateway = LLMGateway(environ={"GEMINI_API_KEY": "not-a-real-test-secret"})
    request = httpx.Request("POST", "https://example.invalid")
    response = httpx.Response(401, request=request)

    def fail_request(*_args, **_kwargs):
        raise httpx.HTTPStatusError(
            "secret-bearing provider body must never appear in logs",
            request=request,
            response=response,
        )

    monkeypatch.setattr(gateway, "_generate_with", fail_request)
    with caplog.at_level("WARNING", logger="finzanjir_ai.answer.providers"):
        assert gateway.generate_json(system="private prompt", prompt="private user text") is None

    assert "provider=gemini" in caplog.text
    assert "category=authentication_or_permission_failed" in caplog.text
    assert "http_status=401" in caplog.text
    assert "secret-bearing" not in caplog.text
    assert "not-a-real-test-secret" not in caplog.text
    assert "private prompt" not in caplog.text
    assert "private user text" not in caplog.text



def test_gateway_logs_safe_http_status_for_request_rejection(caplog, monkeypatch):
    gateway = LLMGateway(environ={"OPENROUTER_API_KEY": "not-a-real-test-secret"})
    request = httpx.Request("POST", "https://example.invalid")
    response = httpx.Response(402, request=request)

    def fail_request(*_args, **_kwargs):
        raise httpx.HTTPStatusError(
            "payment details and private body must not be logged",
            request=request,
            response=response,
        )

    monkeypatch.setattr(gateway, "_generate_with", fail_request)
    with caplog.at_level("WARNING", logger="finzanjir_ai.answer.providers"):
        assert gateway.generate_json(system="private prompt", prompt="private user text") is None

    assert "provider=openrouter" in caplog.text
    assert "category=request_rejected" in caplog.text
    assert "http_status=402" in caplog.text
    assert "payment details" not in caplog.text
    assert "not-a-real-test-secret" not in caplog.text
    assert "private prompt" not in caplog.text
    assert "private user text" not in caplog.text


def test_explicit_offline_policy_disables_all_hosted_providers_even_with_keys():
    gateway = LLMGateway(environ={
        "FINZANJIR_LLM_PROVIDER": "offline",
        "GEMINI_API_KEY": "must-not-be-used",
        "OPENROUTER_API_KEY": "must-not-be-used",
    })
    assert gateway.configured_providers() == ()
    assert gateway.generate_json(system="system", prompt="prompt") is None
    assert gateway.last_status == "offline_mode"
    assert gateway.last_provider_failures == []


def test_offline_query_expansion_never_calls_network(monkeypatch):
    gateway = LLMGateway(environ={
        "FINZANJIR_LLM_PROVIDER": "offline",
        "GEMINI_API_KEY": "must-not-be-used",
        "OPENROUTER_API_KEY": "must-not-be-used",
    })

    def forbidden_network_call(*_args, **_kwargs):
        raise AssertionError("offline mode attempted a hosted provider call")

    monkeypatch.setattr(gateway, "_generate_with", forbidden_network_call)
    assert gateway.expand_question("FINZANJIR nima uchun kerak?") == ()
    assert gateway.last_status == "offline_mode"


def test_none_and_disabled_are_explicit_offline_aliases():
    for policy in ("none", "disabled"):
        gateway = LLMGateway(environ={
            "FINZANJIR_LLM_PROVIDER": policy,
            "GEMINI_API_KEY": "must-not-be-used",
        })
        assert gateway.configured_providers() == ()
        assert gateway.generate_json(system="system", prompt="prompt") is None
        assert gateway.last_status == "offline_mode"

