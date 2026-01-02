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
    assert captured["body"]["instructions"] == "sys"
    assert "system" not in captured["body"]


@pytest.mark.parametrize(
    "base_url",
    [
        "https://api.openai.com",
        "https://api.openai.com/",
        "https://api.openai.com/v1",
        "https://api.openai.com/v1/",
    ],
)
def test_openai_provider_normalizes_base_url(monkeypatch, base_url):
    captured = {}

    def fake_post_json(**kwargs):
        captured["url"] = kwargs["url"]
        return {"output_text": "ok"}

    monkeypatch.setattr("namel3ss.runtime.ai.providers.openai.post_json", fake_post_json)
    provider = OpenAIProvider(api_key="token", base_url=base_url)
    resp = provider.ask(model="gpt-4.1", system_prompt=None, user_input="hi")
    assert resp.output == "ok"
    assert captured["url"] == "https://api.openai.com/v1/responses"


def test_openai_provider_missing_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("NAMEL3SS_OPENAI_API_KEY", raising=False)
    provider = OpenAIProvider(api_key=None)
    with pytest.raises(Namel3ssError) as err:
        provider.ask(model="gpt-4.1", system_prompt=None, user_input="hi")
    assert "Missing OpenAI API key" in str(err.value)


def test_openai_provider_falls_back_to_openai_env(monkeypatch):
    captured = {}

    def fake_post_json(**kwargs):
        captured["headers"] = kwargs["headers"]
        return {"output_text": "hello"}

    monkeypatch.setenv("OPENAI_API_KEY", "env-key")
    monkeypatch.delenv("NAMEL3SS_OPENAI_API_KEY", raising=False)
    monkeypatch.setattr("namel3ss.runtime.ai.providers.openai.post_json", fake_post_json)
    provider = OpenAIProvider(api_key=None)
    resp = provider.ask(model="gpt-4.1", system_prompt=None, user_input="hi")
    assert resp.output == "hello"
    assert captured["headers"]["Authorization"] == "Bearer env-key"


def test_openai_provider_prefers_namel3ss_env(monkeypatch):
    captured = {}

    def fake_post_json(**kwargs):
        captured["headers"] = kwargs["headers"]
        return {"output_text": "hello"}

    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
    monkeypatch.setenv("NAMEL3SS_OPENAI_API_KEY", "namel3ss-key")
    monkeypatch.setattr("namel3ss.runtime.ai.providers.openai.post_json", fake_post_json)
    provider = OpenAIProvider(api_key=None)
    resp = provider.ask(model="gpt-4.1", system_prompt=None, user_input="hi")
    assert resp.output == "hello"
    assert captured["headers"]["Authorization"] == "Bearer namel3ss-key"


def test_openai_provider_http_errors(monkeypatch):
    provider = OpenAIProvider(api_key="token")

    def fake_post_json(**kwargs):
        raise map_http_error("openai", HTTPError(url="u", code=401, msg="", hdrs=None, fp=None))

    monkeypatch.setattr("namel3ss.runtime.ai.providers.openai.post_json", fake_post_json)
    with pytest.raises(Namel3ssError) as err:
        provider.ask(model="gpt-4.1", system_prompt=None, user_input="hi")
    message = str(err.value)
    diagnostic = err.value.details.get("diagnostic") if isinstance(err.value.details, dict) else None
    assert "provider=openai" in message
    assert "/v1/responses" in message
    assert "status=401" in message
    assert diagnostic["provider"] == "openai"
    assert diagnostic["url"].endswith("/v1/responses")
    assert diagnostic["status"] == 401

    def fake_post_json2(**kwargs):
        raise map_http_error("openai", URLError("bad"))

    monkeypatch.setattr("namel3ss.runtime.ai.providers.openai.post_json", fake_post_json2)
    with pytest.raises(Namel3ssError) as err:
        provider.ask(model="gpt-4.1", system_prompt=None, user_input="hi")
    message = str(err.value)
    diagnostic = err.value.details.get("diagnostic") if isinstance(err.value.details, dict) else None
    assert "provider=openai" in message
    assert "/v1/responses" in message
    assert "unreachable" in message
    assert diagnostic["provider"] == "openai"
    assert diagnostic["url"].endswith("/v1/responses")


def test_openai_provider_error_diagnostics_redacted(monkeypatch):
    def fake_post_json(**kwargs):
        details = {
            "status": 401,
            "error": {
                "code": "invalid_api_key",
                "type": "invalid_request_error",
                "message": "Invalid API key: sk-test-secret",
            },
        }
        raise Namel3ssError("Provider 'openai' authentication failed", details=details)

    monkeypatch.setattr("namel3ss.runtime.ai.providers.openai.post_json", fake_post_json)
    provider = OpenAIProvider(api_key="sk-test-secret")
    with pytest.raises(Namel3ssError) as err:
        provider.ask(model="gpt-4.1", system_prompt=None, user_input="hi")
    message = str(err.value)
    diagnostic = err.value.details.get("diagnostic") if isinstance(err.value.details, dict) else None
    assert "provider=openai" in message
    assert "/v1/responses" in message
    assert "status=401" in message
    assert "code=invalid_api_key" in message
    assert "type=invalid_request_error" in message
    assert "sk-" not in message
    assert diagnostic["provider"] == "openai"
    assert diagnostic["code"] == "invalid_api_key"
    assert diagnostic["type"] == "invalid_request_error"
    assert diagnostic["message"]
    assert "sk-" not in diagnostic["message"]


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
