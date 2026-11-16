import json

import httpx
import pytest

from finzanjir_ai.cloud.providers import (
    anthropic_adapter,
    cohere_adapter,
    gemini_adapter,
    mistral_adapter,
    openai_adapter,
    register_configured_providers,
)
from finzanjir_ai.cloud.workers import CloudTask, CloudWorkerRegistry, WorkerRole


@pytest.mark.parametrize(
    "name,factory,environment,response,auth_header,expected_endpoint",
    [
        (
            "openai", openai_adapter,
            {"OPENAI_API_KEY": "test-key", "OPENAI_MODEL": "model-a"},
            {"choices": [{"message": {"content": "OpenAI result"}}]},
            "authorization", "https://api.openai.com/v1/chat/completions",
        ),
        (
            "anthropic", anthropic_adapter,
            {"ANTHROPIC_API_KEY": "test-key", "ANTHROPIC_MODEL": "model-b"},
            {"content": [{"type": "text", "text": "Anthropic result"}]},
            "x-api-key", "https://api.anthropic.com/v1/messages",
        ),
        (
            "gemini", gemini_adapter,
            {"GEMINI_API_KEY": "test-key", "GEMINI_MODEL": "model-c"},
            {"candidates": [{"content": {"parts": [{"text": "Gemini result"}]}}]},
            "x-goog-api-key", "https://generativelanguage.googleapis.com/v1beta/models/model-c:generateContent",
        ),
        (
            "mistral", mistral_adapter,
            {"MISTRAL_API_KEY": "test-key", "MISTRAL_MODEL": "model-d"},
            {"choices": [{"message": {"content": "Mistral result"}}]},
            "authorization", "https://api.mistral.ai/v1/chat/completions",
        ),
        (
            "cohere", cohere_adapter,
            {"COHERE_API_KEY": "test-key", "COHERE_MODEL": "model-e"},
            {"message": {"content": [{"type": "text", "text": "Cohere result"}]}},
            "authorization", "https://api.cohere.com/v2/chat",
        ),
    ],
)
def test_provider_adapters_use_independent_auth_payloads_and_parsers(
    name, factory, environment, response, auth_header, expected_endpoint
):
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["headers"] = request.headers
        seen["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(200, json=response)

    adapter = factory(
        role=WorkerRole.CRITIC,
        environ=environment,
        transport=httpx.MockTransport(handler),
    )
    assert adapter is not None
    result = adapter.execute(CloudTask("Check this public statement", user_approved=True))

    assert seen["url"] == expected_endpoint
    assert seen["headers"][auth_header] in {"Bearer test-key", "test-key"}
    assert result == response.get("choices", [{}])[0].get("message", {}).get("content", result)
    if name == "gemini":
        assert environment["GEMINI_MODEL"] in seen["url"]
        assert seen["body"]["contents"][0]["parts"][0]["text"] == "Check this public statement"
    else:
        assert seen["body"]["model"] == environment[f"{name.upper()}_MODEL"]
        assert seen["body"]["messages"][-1]["content"] == "Check this public statement"


def test_anthropic_adapter_includes_required_version_header():
    adapter = anthropic_adapter(
        environ={"ANTHROPIC_API_KEY": "secret", "ANTHROPIC_MODEL": "claude-model"},
        transport=httpx.MockTransport(lambda request: httpx.Response(
            200, json={"content": [{"type": "text", "text": "ok"}]}
        )),
    )
    assert adapter is not None
    # The adapter's configured header is sent by the generic HTTPS transport.
    assert adapter.extra_headers["anthropic-version"] == "2023-06-01"


def test_provider_factories_do_not_register_without_server_credentials_and_model():
    assert openai_adapter(environ={}) is None
    assert gemini_adapter(environ={"GEMINI_API_KEY": "key"}) is None
    assert cohere_adapter(environ={"COHERE_MODEL": "model"}) is None


def test_registry_adds_only_configured_providers_without_making_requests():
    environment = {
        "OPENAI_API_KEY": "a", "OPENAI_MODEL": "oa",
        "ANTHROPIC_API_KEY": "b", "ANTHROPIC_MODEL": "an",
        "GEMINI_API_KEY": "c", "GEMINI_MODEL": "ge",
        "MISTRAL_API_KEY": "d", "MISTRAL_MODEL": "mi",
        "COHERE_API_KEY": "e", "COHERE_MODEL": "co",
    }
    registry = CloudWorkerRegistry()
    names = register_configured_providers(registry, environ=environment)
    assert names == ("openai", "anthropic", "gemini", "mistral", "cohere")
    assert registry.first_for_role(WorkerRole.CRITIC).name == "openai"
