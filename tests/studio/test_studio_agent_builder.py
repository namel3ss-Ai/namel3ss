from pathlib import Path

from namel3ss.studio.agent_builder.panel import get_agents_payload, run_agent_payload
from namel3ss.studio.agent_builder.wizard import apply_agent_wizard
from namel3ss.studio.session import SessionState


BASE_SOURCE = '''spec is "1.0"

flow "demo":
  return "ok"
'''


AGENT_SOURCE = '''spec is "1.0"

ai "assistant":
  model is "mock-model"
  system_prompt is "Be helpful."

agent "support":
  ai is "assistant"
  system_prompt is "Help."

flow "demo":
  run agent "support" with input: "Hello" as reply
  return reply
'''


EXPECTED_ROUTER = '''spec is "1.0"

flow "demo":
  return "ok"

ai "router_ai":
  provider is "mock"
  model is "mock-model"
  system_prompt is "Route requests to the right specialist."
  memory:
    short_term is 0
    semantic is false
    profile is false

agent "billing_agent":
  ai is "router_ai"
  system_prompt is "Handle billing questions."

agent "sales_agent":
  ai is "router_ai"
  system_prompt is "Handle sales questions."

agent "support_agent":
  ai is "router_ai"
  system_prompt is "Handle support questions."

flow "router_run":
  let topic is input.topic
  let message is input.message
  if topic is "billing":
    run agent "billing_agent" with input: message as reply
    return reply
  if topic is "sales":
    run agent "sales_agent" with input: message as reply
    return reply
  run agent "support_agent" with input: message as reply
  return reply
'''


def test_agent_wizard_router_output(tmp_path):
    app_path = tmp_path / "app.ai"
    app_path.write_text(BASE_SOURCE, encoding="utf-8")
    payload = {
        "pattern": "router",
        "create_ai": True,
        "ai_name": "router_ai",
        "ai_provider": "mock",
        "ai_model": "mock-model",
        "ai_memory": "minimal",
        "ai_tools": [],
        "agents": {
            "billing": "billing_agent",
            "sales": "sales_agent",
            "support": "support_agent",
        },
    }
    result = apply_agent_wizard(BASE_SOURCE, app_path.as_posix(), payload)
    assert result["ok"] is True
    assert app_path.as_posix() in result["updated_files"]
    assert app_path.read_text(encoding="utf-8") == EXPECTED_ROUTER


def test_agent_panel_lists_agents(tmp_path):
    app_path = tmp_path / "app.ai"
    app_path.write_text(AGENT_SOURCE, encoding="utf-8")
    payload = get_agents_payload(AGENT_SOURCE, SessionState(), app_path.as_posix())
    assert payload["ok"] is True
    assert payload["agents"] == [
        {"name": "support", "ai_name": "assistant", "system_prompt": "Help."},
    ]


def test_agent_run_returns_trace(tmp_path):
    app_path = tmp_path / "app.ai"
    app_path.write_text(AGENT_SOURCE, encoding="utf-8")
    session = SessionState()
    payload = run_agent_payload(
        AGENT_SOURCE,
        session,
        app_path.as_posix(),
        {"agent": "support", "input": "Hello"},
    )
    assert payload["ok"] is True
    assert isinstance(payload.get("result"), str)
    assert payload["result"].startswith("[mock-model]")
    assert "agent_explain" in payload
    assert payload["agent_explain"]["summaries"]
    traces = payload.get("traces") or []
    assert traces
    trace = traces[0]
    assert trace.get("agent_name") == "support"
    assert trace.get("ai_name") == "assistant"
