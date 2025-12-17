import json
from urllib.error import HTTPError, URLError

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.ai.providers.openai import OpenAIProvider
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


def test_openai_provider_sends_expected_payload(monkeypatch):
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.get_full_url()
        captured["headers"] = {k.lower(): v for k, v in req.headers.items()}
        captured["body"] = json.loads(req.data.decode())
        return _DummyResponse(b'{"output_text":"hello"}')

    provider = OpenAIProvider(api_key="token", base_url="https://api.custom")
    monkeypatch.setattr("namel3ss.runtime.ai.http.client.urlopen", fake_urlopen)
    resp = provider.ask(model="gpt-4.1", system_prompt="sys", user_input="hi")
    assert resp.output == "hello"
    assert captured["url"] == "https://api.custom/v1/responses"
    assert captured["headers"]["authorization"] == "Bearer token"
    assert captured["headers"]["content-type"] == "application/json"
    assert captured["body"]["model"] == "gpt-4.1"
    assert captured["body"]["input"] == "hi"
    assert captured["body"]["system"] == "sys"


def test_openai_provider_missing_key(monkeypatch):
    provider = OpenAIProvider(api_key=None)
    with pytest.raises(Namel3ssError) as err:
        provider.ask(model="gpt-4.1", system_prompt=None, user_input="hi")
    assert "requires NAMEL3SS_OPENAI_API_KEY" in str(err.value)


def test_openai_provider_http_errors(monkeypatch):
    provider = OpenAIProvider(api_key="token")

    def fake_post_json(**kwargs):
        raise map_http_error("openai", HTTPError(url="u", code=401, msg="", hdrs=None, fp=None))

    monkeypatch.setattr("namel3ss.runtime.ai.providers.openai.post_json", fake_post_json)
    with pytest.raises(Namel3ssError) as err:
        provider.ask(model="gpt-4.1", system_prompt=None, user_input="hi")
    assert "authentication failed" in str(err.value)

    def fake_post_json2(**kwargs):
        raise map_http_error("openai", URLError("bad"))

    monkeypatch.setattr("namel3ss.runtime.ai.providers.openai.post_json", fake_post_json2)
    with pytest.raises(Namel3ssError) as err:
        provider.ask(model="gpt-4.1", system_prompt=None, user_input="hi")
    assert "unreachable" in str(err.value)


def test_openai_provider_bad_shape(monkeypatch):
    provider = OpenAIProvider(api_key="token")

    def fake_urlopen(req, timeout=None):
        return _DummyResponse(b'{"no_text": true}')

    monkeypatch.setattr("namel3ss.runtime.ai.http.client.urlopen", fake_urlopen)
    with pytest.raises(Namel3ssError) as err:
        provider.ask(model="gpt-4.1", system_prompt=None, user_input="hi")
    assert "invalid response" in str(err.value)


def test_openai_parses_output_variants(monkeypatch):
    provider = OpenAIProvider(api_key="token")

    def fake_urlopen(req, timeout=None):
        return _DummyResponse(b'{"output":[{"content":[{"text":"hi"}]}]}')

    monkeypatch.setattr("namel3ss.runtime.ai.http.client.urlopen", fake_urlopen)
    resp = provider.ask(model="gpt-4.1", system_prompt=None, user_input="hi")
    assert resp.output == "hi"

    def fake_urlopen2(req, timeout=None):
        return _DummyResponse(b'{"output_text":"hello"}')

    monkeypatch.setattr("namel3ss.runtime.ai.http.client.urlopen", fake_urlopen2)
    resp2 = provider.ask(model="gpt-4.1", system_prompt=None, user_input="hi")
    assert resp2.output == "hello"
