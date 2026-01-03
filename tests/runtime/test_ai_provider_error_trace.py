from __future__ import annotations

import io
import json
import ssl
from urllib.error import HTTPError
from urllib.error import URLError

from namel3ss.runtime.executor import execute_flow
from namel3ss.traces.schema import TraceEventType
from tests.conftest import lower_ir_program


SOURCE = '''spec is "1.0"

ai "assistant":
  provider is "openai"
  model is "gpt-4.1"

ai "fallback":
  provider is "mock"
  model is "mock-model"

flow "demo":
  try:
    ask ai "assistant" with input: "hi" as reply
  with catch err:
    ask ai "fallback" with input: "hi" as reply
  return reply
'''


def test_openai_failure_emits_diagnostic_trace(monkeypatch):
    program = lower_ir_program(SOURCE)
    body = json.dumps(
        {
            "error": {
                "code": "invalid_api_key",
                "type": "invalid_request_error",
                "message": "Invalid API key: sk-test-secret",
            }
        }
    ).encode()

    def fake_urlopen(req, timeout=None):
        raise HTTPError(url=req.get_full_url(), code=401, msg="Unauthorized", hdrs=None, fp=io.BytesIO(body))

    monkeypatch.setenv("NAMEL3SS_OPENAI_API_KEY", "sk-test-secret")
    monkeypatch.setattr("namel3ss.runtime.ai.http.client.urlopen", fake_urlopen)
    result = execute_flow(
        program.flows[0],
        schemas={schema.name: schema for schema in program.records},
        initial_state={},
        ai_profiles=program.ais,
    )
    assert "[mock-model]" in result.last_value
    error_events = []
    for trace in _ai_traces(result.traces):
        for event in trace.canonical_events:
            if event.get("type") == TraceEventType.AI_PROVIDER_ERROR:
                error_events.append(event)
    assert error_events
    diagnostic = error_events[0].get("diagnostic") or {}
    assert diagnostic.get("provider") == "openai"
    assert str(diagnostic.get("url", "")).endswith("/v1/responses")
    assert diagnostic.get("status") == 401
    assert "sk-" not in str(diagnostic.get("message", ""))


def test_openai_network_error_in_trace(monkeypatch):
    program = lower_ir_program(SOURCE)

    def fake_urlopen(req, timeout=None):
        raise URLError(ssl.SSLError("CERTIFICATE_VERIFY_FAILED"))

    monkeypatch.setenv("NAMEL3SS_OPENAI_API_KEY", "sk-test-secret")
    monkeypatch.setattr("namel3ss.runtime.ai.http.client.urlopen", fake_urlopen)
    result = execute_flow(
        program.flows[0],
        schemas={schema.name: schema for schema in program.records},
        initial_state={},
        ai_profiles=program.ais,
    )
    assert "[mock-model]" in result.last_value
    error_events = []
    for trace in _ai_traces(result.traces):
        for event in trace.canonical_events:
            if event.get("type") == TraceEventType.AI_PROVIDER_ERROR:
                error_events.append(event)
    assert error_events
    diagnostic = error_events[0].get("diagnostic") or {}
    network_error = diagnostic.get("network_error") if isinstance(diagnostic, dict) else None
    assert network_error
    assert network_error.get("name") == "SSLError"
    assert "CERTIFICATE_VERIFY_FAILED" in str(network_error.get("message", ""))
    assert "sk-" not in str(diagnostic.get("message", ""))
    assert "Bearer" not in str(diagnostic.get("message", ""))


def _ai_traces(traces):
    return [trace for trace in traces if hasattr(trace, "canonical_events")]
