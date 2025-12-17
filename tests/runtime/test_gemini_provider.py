import json
from urllib.error import HTTPError, URLError

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.ai.providers.gemini import GeminiProvider
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


def test_gemini_payload(monkeypatch):
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.get_full_url()
        captured["headers"] = {k.lower(): v for k, v in req.headers.items()}
        captured["body"] = json.loads(req.data.decode())
        return _DummyResponse(b'{"candidates":[{"content":{"parts":[{"text":"hi there"}]}}]}')

    provider = GeminiProvider(api_key="key")
    monkeypatch.setattr("namel3ss.runtime.ai.http.client.urlopen", fake_urlopen)
    resp = provider.ask(model="gemini-1.5", system_prompt="sys", user_input="hi")
    assert resp.output == "hi there"
    assert "models/gemini-1.5:generateContent?key=key" in captured["url"]
    assert captured["headers"]["content-type"] == "application/json"
    assert captured["body"]["contents"][0]["parts"][0]["text"].startswith("sys")


def test_gemini_missing_key():
    provider = GeminiProvider(api_key=None)
    with pytest.raises(Namel3ssError):
        provider.ask(model="gemini-1.5", system_prompt=None, user_input="hi")


def test_gemini_errors(monkeypatch):
    provider = GeminiProvider(api_key="key")

    def fake_post_json(**kwargs):
        raise map_http_error("gemini", HTTPError(url="u", code=401, msg="", hdrs=None, fp=None))

    monkeypatch.setattr("namel3ss.runtime.ai.providers.gemini.post_json", fake_post_json)
    with pytest.raises(Namel3ssError) as err:
        provider.ask(model="gemini-1.5", system_prompt=None, user_input="hi")
    assert "authentication failed" in str(err.value)

    def fake_post_json2(**kwargs):
        raise map_http_error("gemini", URLError("bad"))

    monkeypatch.setattr("namel3ss.runtime.ai.providers.gemini.post_json", fake_post_json2)
    with pytest.raises(Namel3ssError) as err:
        provider.ask(model="gemini-1.5", system_prompt=None, user_input="hi")
    assert "unreachable" in str(err.value)


def test_gemini_invalid(monkeypatch):
    provider = GeminiProvider(api_key="key")

    def fake_urlopen(req, timeout=None):
        return _DummyResponse(b'{"candidates":[]}')

    monkeypatch.setattr("namel3ss.runtime.ai.http.client.urlopen", fake_urlopen)
    with pytest.raises(Namel3ssError) as err:
        provider.ask(model="gemini-1.5", system_prompt=None, user_input="hi")
    assert "invalid response" in str(err.value)


def test_gemini_multiple_parts(monkeypatch):
    provider = GeminiProvider(api_key="key")

    def fake_urlopen(req, timeout=None):
        return _DummyResponse(
            b'{"candidates":[{"content":{"parts":[{"text":"a"},{"text":"b"}]}}]}'
        )

    monkeypatch.setattr("namel3ss.runtime.ai.http.client.urlopen", fake_urlopen)
    resp = provider.ask(model="gemini-1.5", system_prompt=None, user_input="hi")
    assert resp.output == "a\nb"
