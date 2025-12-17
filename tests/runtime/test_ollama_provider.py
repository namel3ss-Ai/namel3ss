from urllib.error import URLError

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.ai.providers._shared.errors import map_http_error
from namel3ss.runtime.ai.providers.ollama import OllamaProvider


class _DummyResponse:
    def __init__(self, payload: bytes):
        self.payload = payload

    def read(self):
        return self.payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_ollama_provider_returns_output(monkeypatch):
    provider = OllamaProvider(host="http://ollama.test", timeout_seconds=1)

    def fake_post_json(**kwargs):
        return {"message": {"content": "hello world"}}

    monkeypatch.setattr("namel3ss.runtime.ai.providers.ollama.post_json", fake_post_json)
    resp = provider.ask(model="llama3.1", system_prompt="hi", user_input="test")
    assert resp.output == "hello world"


def test_ollama_provider_handles_errors(monkeypatch):
    provider = OllamaProvider(host="http://bad-host", timeout_seconds=1)

    def fake_post_json(**kwargs):
        raise map_http_error("ollama", URLError("connection refused"))

    monkeypatch.setattr("namel3ss.runtime.ai.providers.ollama.post_json", fake_post_json)
    with pytest.raises(Namel3ssError) as err:
        provider.ask(model="llama3.1", system_prompt=None, user_input="test")
    assert "Provider 'ollama' unreachable" in str(err.value)


def test_ollama_invalid_json(monkeypatch):
    provider = OllamaProvider(host="http://ollama.test", timeout_seconds=1)

    def fake_post_json(**kwargs):
        raise Namel3ssError("Provider 'ollama' returned an invalid response")

    monkeypatch.setattr("namel3ss.runtime.ai.providers.ollama.post_json", fake_post_json)
    with pytest.raises(Namel3ssError) as err:
        provider.ask(model="llama3.1", system_prompt=None, user_input="test")
    assert "Provider 'ollama' returned an invalid response" in str(err.value)
