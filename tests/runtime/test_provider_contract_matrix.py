import json
from urllib.error import HTTPError, URLError

import pytest

from namel3ss.config.model import AppConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.ai.providers.anthropic import AnthropicProvider
from namel3ss.runtime.ai.providers.gemini import GeminiProvider
from namel3ss.runtime.ai.providers.mistral import MistralProvider
from namel3ss.runtime.ai.providers.ollama import OllamaProvider
from namel3ss.runtime.ai.providers.openai import OpenAIProvider


class _DummyResponse:
    def __init__(self, payload: bytes):
        self.payload = payload

    def read(self):
        return self.payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


PROVIDERS = {
    "ollama": lambda: OllamaProvider(host="http://127.0.0.1:11434", timeout_seconds=1),
    "openai": lambda: OpenAIProvider(api_key="key", base_url="https://api.openai.com"),
    "anthropic": lambda: AnthropicProvider(api_key="key"),
    "gemini": lambda: GeminiProvider(api_key="key"),
    "mistral": lambda: MistralProvider(api_key="key"),
}


@pytest.mark.parametrize("name", ["openai", "anthropic", "gemini", "mistral"])
def test_missing_key_errors(name):
    provider = PROVIDERS[name]().__class__(api_key=None)
    with pytest.raises(Namel3ssError) as err:
        provider.ask(model="m", system_prompt=None, user_input="hi")
    assert str(err.value) == f"Provider '{name}' requires NAMEL3SS_{name.upper()}_API_KEY"


@pytest.mark.parametrize("name", ["ollama", "openai", "anthropic", "gemini", "mistral"])
def test_unreachable_errors(monkeypatch, name):
    provider = PROVIDERS[name]()

    def fake_urlopen(req, timeout=None):
        raise URLError("fail")

    monkeypatch.setattr("namel3ss.runtime.ai.http.client.urlopen", fake_urlopen)
    with pytest.raises(Namel3ssError) as err:
        provider.ask(model="m", system_prompt=None, user_input="hi")
    assert str(err.value) == f"Provider '{name}' unreachable"


@pytest.mark.parametrize("name", ["ollama", "openai", "anthropic", "gemini", "mistral"])
def test_invalid_json_errors(monkeypatch, name):
    provider = PROVIDERS[name]()

    def fake_urlopen(req, timeout=None):
        return _DummyResponse(b"not-json")

    monkeypatch.setattr("namel3ss.runtime.ai.http.client.urlopen", fake_urlopen)
    with pytest.raises(Namel3ssError) as err:
        provider.ask(model="m", system_prompt=None, user_input="hi")
    assert str(err.value) == f"Provider '{name}' returned an invalid response"


@pytest.mark.parametrize("name", ["ollama", "openai", "anthropic", "gemini", "mistral"])
def test_invalid_shape_errors(monkeypatch, name):
    provider = PROVIDERS[name]()

    def fake_urlopen(req, timeout=None):
        return _DummyResponse(json.dumps({"ok": True}).encode())

    monkeypatch.setattr("namel3ss.runtime.ai.http.client.urlopen", fake_urlopen)
    with pytest.raises(Namel3ssError) as err:
        provider.ask(model="m", system_prompt=None, user_input="hi")
    assert str(err.value) == f"Provider '{name}' returned an invalid response"


@pytest.mark.parametrize("name", ["openai", "anthropic", "gemini", "mistral"])
def test_empty_output_errors(monkeypatch, name):
    provider = PROVIDERS[name]()
    payloads = {
        "openai": {"output_text": "   "},
        "anthropic": {"content": [{"text": "  "}]},
        "gemini": {"candidates": [{"content": {"parts": [{"text": ""}]}}]},
        "mistral": {"choices": [{"message": {"content": ""}}]},
    }

    def fake_urlopen(req, timeout=None):
        return _DummyResponse(json.dumps(payloads[name]).encode())

    monkeypatch.setattr("namel3ss.runtime.ai.http.client.urlopen", fake_urlopen)
    with pytest.raises(Namel3ssError) as err:
        provider.ask(model="m", system_prompt=None, user_input="hi")
    assert str(err.value) == f"Provider '{name}' returned an invalid response"
