import json
from urllib.error import HTTPError, URLError

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.ai.providers.mistral import MistralProvider
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


def test_mistral_payload(monkeypatch):
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.get_full_url()
        captured["headers"] = {k.lower(): v for k, v in req.headers.items()}
        captured["body"] = json.loads(req.data.decode())
        return _DummyResponse(b'{"choices":[{"message":{"content":"ok"}}]}')

    provider = MistralProvider(api_key="key")
    monkeypatch.setattr("namel3ss.runtime.ai.http.client.urlopen", fake_urlopen)
    resp = provider.ask(model="mistral-medium", system_prompt="sys", user_input="hi")
    assert resp.output == "ok"
    assert captured["url"] == "https://api.mistral.ai/v1/chat/completions"
    assert captured["headers"]["authorization"] == "Bearer key"
    assert captured["headers"]["content-type"] == "application/json"
    assert captured["body"]["messages"][0]["role"] == "system"
    assert captured["body"]["messages"][1]["content"] == "hi"


def test_mistral_missing_key():
    provider = MistralProvider(api_key=None)
    with pytest.raises(Namel3ssError):
        provider.ask(model="mistral-medium", system_prompt=None, user_input="hi")


def test_mistral_errors(monkeypatch):
    provider = MistralProvider(api_key="key")

    def fake_post_json(**kwargs):
        raise map_http_error("mistral", HTTPError(url="u", code=403, msg="", hdrs=None, fp=None))

    monkeypatch.setattr("namel3ss.runtime.ai.providers.mistral.post_json", fake_post_json)
    with pytest.raises(Namel3ssError) as err:
        provider.ask(model="mistral-medium", system_prompt=None, user_input="hi")
    assert "authentication failed" in str(err.value)

    def fake_post_json2(**kwargs):
        raise map_http_error("mistral", URLError("bad"))

    monkeypatch.setattr("namel3ss.runtime.ai.providers.mistral.post_json", fake_post_json2)
    with pytest.raises(Namel3ssError) as err:
        provider.ask(model="mistral-medium", system_prompt=None, user_input="hi")
    assert "unreachable" in str(err.value)


def test_mistral_invalid(monkeypatch):
    provider = MistralProvider(api_key="key")

    def fake_urlopen(req, timeout=None):
        return _DummyResponse(b'{"choices":[]}')

    monkeypatch.setattr("namel3ss.runtime.ai.http.client.urlopen", fake_urlopen)
    with pytest.raises(Namel3ssError) as err:
        provider.ask(model="mistral-medium", system_prompt=None, user_input="hi")
    assert "invalid response" in str(err.value)


def test_mistral_parses_message(monkeypatch):
    provider = MistralProvider(api_key="key")

    def fake_urlopen(req, timeout=None):
        return _DummyResponse(b'{"choices":[{"message":{"content":"hello"}}]}')

    monkeypatch.setattr("namel3ss.runtime.ai.http.client.urlopen", fake_urlopen)
    resp = provider.ask(model="mistral-medium", system_prompt=None, user_input="hi")
    assert resp.output == "hello"
