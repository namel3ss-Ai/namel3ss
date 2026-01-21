from __future__ import annotations

import json
from pathlib import Path

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.executor import Executor
from namel3ss.runtime.store.memory_store import MemoryStore
from tests.conftest import lower_ir_program


class FakeHeaders:
    def __init__(self, items: list[tuple[str, str]]):
        self._items = items

    def items(self):
        return list(self._items)


class FakeResponse:
    def __init__(self, body: str, headers: list[tuple[str, str]], status: int = 200):
        self._body = body.encode("utf-8")
        self.status = status
        self.headers = FakeHeaders(headers)

    def read(self):
        return self._body

    def getcode(self):
        return self.status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def _build_executor(tmp_path: Path, source: str) -> Executor:
    program = lower_ir_program(source)
    app_path = tmp_path / "app.ai"
    app_path.write_text(source, encoding="utf-8")
    flow = program.flows[0]
    return Executor(
        flow,
        schemas={},
        store=MemoryStore(),
        tools=program.tools,
        functions=program.functions,
        agents=program.agents,
        ai_profiles=program.ais,
        jobs={job.name: job for job in program.jobs},
        job_order=[job.name for job in program.jobs],
        capabilities=program.capabilities,
        project_root=str(tmp_path),
        app_path=app_path.as_posix(),
    )


def test_auth_helpers_redact_secret_in_traces(monkeypatch, tmp_path: Path) -> None:
    source = '''spec is "1.0"

capabilities:
  http
  secrets

tool "fetch status":
  implemented using http

  input:
    url is text
    headers is optional json

  output:
    status is number
    body is text

flow "demo":
  let headers is auth_bearer(secret("stripe_key"))
  let response is fetch status:
    url is "https://example.com"
    headers is headers
  return response
'''
    secret_value = "sk_test_123"
    monkeypatch.setenv("N3_SECRET_STRIPE_KEY", secret_value)
    captured: dict[str, str] = {}

    def fake_urlopen(req, timeout):
        captured.update({key.lower(): value for key, value in req.header_items()})
        return FakeResponse("ok", [("Content-Type", "text/plain")], status=200)

    monkeypatch.setattr("namel3ss.runtime.backend.http_capability.safe_urlopen", fake_urlopen)

    executor = _build_executor(tmp_path, source)
    result = executor.run()

    assert captured.get("authorization") == f"Bearer {secret_value}"

    http_events = [
        event for event in result.traces if isinstance(event, dict) and event.get("kind") == "http"
    ]
    assert http_events
    event = http_events[-1]
    auth_headers = [item for item in event["input"]["headers"] if item.get("name") == "Authorization"]
    assert auth_headers
    assert auth_headers[0]["value"] == "Bearer [redacted: stripe_key]"

    dumped = json.dumps(result.traces, default=str)
    assert secret_value not in dumped


def test_secret_requires_secrets_capability(tmp_path: Path) -> None:
    source = '''spec is "1.0"

capabilities:
  http

flow "demo":
  let token is secret("stripe_key")
  return token
'''
    executor = _build_executor(tmp_path, source)
    with pytest.raises(Namel3ssError, match="Secrets capability is not enabled"):
        executor.run()


def test_secret_output_is_redacted(tmp_path: Path, monkeypatch) -> None:
    source = '''spec is "1.0"

capabilities:
  secrets

flow "demo":
  return secret("stripe_key")
'''
    secret_value = "sk_test_123"
    monkeypatch.setenv("N3_SECRET_STRIPE_KEY", secret_value)
    executor = _build_executor(tmp_path, source)
    result = executor.run()
    assert result.last_value == "[redacted: stripe_key]"
    assert secret_value not in str(result.last_value)


def test_auth_helpers_require_http_capability(tmp_path: Path, monkeypatch) -> None:
    source = '''spec is "1.0"

capabilities:
  secrets

flow "demo":
  let headers is auth_bearer(secret("stripe_key"))
  return headers
'''
    monkeypatch.setenv("N3_SECRET_STRIPE_KEY", "sk_test_123")
    executor = _build_executor(tmp_path, source)
    with pytest.raises(Namel3ssError, match="Http capability is not enabled"):
        executor.run()
