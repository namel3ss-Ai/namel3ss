from namel3ss.studio.api import execute_action


def test_execute_action_unknown_returns_error_payload():
    source = 'spec is "1.0"\n\nflow "demo":\n  return "ok"\n'
    payload = execute_action(source, session=None, action_id="unknown", payload={}, app_path="app.ai")
    assert payload["ok"] is False
    assert payload.get("kind") == "engine"
    assert "Unknown action" in payload.get("error", "")
