from urllib.error import URLError

import pytest

from namel3ss.errors.base import Namel3ssError
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

    def fake_urlopen(req, timeout=None):
        payload = b'{"message":{"content":"hello world"}}'
        return _DummyResponse(payload)

    monkeypatch.setattr("namel3ss.runtime.ai.providers.ollama.urlopen", fake_urlopen)
    resp = provider.ask(model="llama3.1", system_prompt="hi", user_input="test")
    assert resp.output == "hello world"


def test_ollama_provider_handles_errors(monkeypatch):
    provider = OllamaProvider(host="http://bad-host", timeout_seconds=1)

    def fake_urlopen(req, timeout=None):
        raise URLError("connection refused")

    monkeypatch.setattr("namel3ss.runtime.ai.providers.ollama.urlopen", fake_urlopen)
    with pytest.raises(Namel3ssError) as err:
        provider.ask(model="llama3.1", system_prompt=None, user_input="test")
    assert "Ollama is not reachable" in str(err.value)
    assert "bad-host" in str(err.value)
