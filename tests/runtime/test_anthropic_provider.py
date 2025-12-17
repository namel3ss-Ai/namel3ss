import json
from urllib.error import HTTPError, URLError

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.ai.providers.anthropic import AnthropicProvider
from namel3ss.runtime.ai.providers._shared.errors import map_http_error


class _DummyResponse:
    def __init__(self, payload: bytes):
        self.payload = payload

    def read(self):
        return self.payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_anthropic_provider_payload(monkeypatch):
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.get_full_url()
        captured["headers"] = {k.lower(): v for k, v in req.headers.items()}
        captured["body"] = json.loads(req.data.decode())
        return _DummyResponse(b'{"content":[{"text":"hello"}]}')

    provider = AnthropicProvider(api_key="key")
    monkeypatch.setattr("namel3ss.runtime.ai.http.client.urlopen", fake_urlopen)
    resp = provider.ask(model="claude-3", system_prompt="sys", user_input="hi")
    assert resp.output == "hello"
    assert captured["url"] == "https://api.anthropic.com/v1/messages"
    assert captured["headers"]["x-api-key"] == "key"
    assert captured["headers"]["anthropic-version"]
    assert captured["headers"]["content-type"] == "application/json"
    assert captured["body"]["model"] == "claude-3"
    assert captured["body"]["messages"][0]["content"] == "hi"
    assert captured["body"]["system"] == "sys"


def test_anthropic_missing_key():
    provider = AnthropicProvider(api_key=None)
    with pytest.raises(Namel3ssError):
        provider.ask(model="claude-3", system_prompt=None, user_input="hi")


def test_anthropic_error_mapping(monkeypatch):
    provider = AnthropicProvider(api_key="key")

    def fake_post_json(**kwargs):
        raise map_http_error("anthropic", HTTPError(url="u", code=403, msg="", hdrs=None, fp=None))

    monkeypatch.setattr("namel3ss.runtime.ai.providers.anthropic.post_json", fake_post_json)
    with pytest.raises(Namel3ssError) as err:
        provider.ask(model="claude-3", system_prompt=None, user_input="hi")
    assert "authentication failed" in str(err.value)

    def fake_post_json2(**kwargs):
        raise map_http_error("anthropic", URLError("bad"))

    monkeypatch.setattr("namel3ss.runtime.ai.providers.anthropic.post_json", fake_post_json2)
    with pytest.raises(Namel3ssError) as err:
        provider.ask(model="claude-3", system_prompt=None, user_input="hi")
    assert "unreachable" in str(err.value)


def test_anthropic_invalid_response(monkeypatch):
    provider = AnthropicProvider(api_key="key")

    def fake_urlopen(req, timeout=None):
        return _DummyResponse(b'{"content":[]}')

    monkeypatch.setattr("namel3ss.runtime.ai.http.client.urlopen", fake_urlopen)
    with pytest.raises(Namel3ssError) as err:
        provider.ask(model="claude-3", system_prompt=None, user_input="hi")
    assert "invalid response" in str(err.value)


def test_anthropic_parses_multiple_content(monkeypatch):
    provider = AnthropicProvider(api_key="key")

    def fake_urlopen(req, timeout=None):
        return _DummyResponse(b'{"content":[{"text":"first"},{"text":"second"}]}')

    monkeypatch.setattr("namel3ss.runtime.ai.http.client.urlopen", fake_urlopen)
    resp = provider.ask(model="claude-3", system_prompt=None, user_input="hi")
    assert resp.output == "first"
