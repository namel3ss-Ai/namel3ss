import http.client
import json

from namel3ss.runtime.dev_server import BrowserAppState, BrowserRunner


APP_SOURCE = '''spec is "1.0"

flow "increment":
  set state.counter is 1
  return state.counter

page "home":
  button "Run":
    calls flow "increment"
'''

APP_SOURCE_RECORDS = '''spec is "1.0"

record "Item":
  field "id" is number must be present
  field "name" is text must be present

flow "seed" requires true:
  set state.item.id is 10
  set state.item.name is "Ten"
  create "Item" with state.item as item
  set state.item.id is 2
  set state.item.name is "Two"
  create "Item" with state.item as item

page "home":
  button "Seed":
    calls flow "seed"
'''


def test_app_state_endpoints(tmp_path):
    """
    Smoke test the in-process app state surface without HTTP.
    """
    app_path = tmp_path / "app.ai"
    app_path.write_text(APP_SOURCE, encoding="utf-8")
    state = BrowserAppState(app_path, mode="run", debug=False, watch_sources=False)

    manifest = state.manifest_payload()
    actions = sorted(manifest.get("actions", {}).keys())
    assert actions

    initial_state = state.state_payload()
    assert initial_state["ok"] is True
    assert initial_state["state"] == {}

    response = state.run_action(actions[0], {})
    assert response["ok"] is True
    assert response["state"]["counter"] == 1

    updated_state = state.state_payload()
    assert updated_state["state"]["counter"] == 1


def test_app_runtime_http_endpoints(tmp_path):
    app_path = tmp_path / "app.ai"
    app_path.write_text(APP_SOURCE, encoding="utf-8")

    runner = BrowserRunner(app_path, mode="run", port=7860, watch_sources=False)
    runner.start(background=True)
    port = runner.bound_port

    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=3)

    conn.request("GET", "/api/ui")
    payload = json.loads(conn.getresponse().read())
    actions = sorted(payload.get("actions", {}).keys())
    assert actions

    action_body = json.dumps({"id": actions[0], "payload": {}})
    conn.request("POST", "/api/action", body=action_body, headers={"Content-Type": "application/json"})
    action_resp = json.loads(conn.getresponse().read())
    assert action_resp["ok"] is True
    assert action_resp["state"]["counter"] == 1

    conn.request("GET", "/api/state")
    state_payload = json.loads(conn.getresponse().read())
    assert state_payload["state"]["counter"] == 1

    conn.request("GET", "/api/health")
    health = json.loads(conn.getresponse().read())
    assert health["status"] == "ready"

    conn.close()
    runner.shutdown()


def test_state_payload_includes_records_and_effects(tmp_path):
    app_path = tmp_path / "app.ai"
    app_path.write_text(APP_SOURCE_RECORDS, encoding="utf-8")
    state = BrowserAppState(app_path, mode="run", debug=False, watch_sources=False)

    manifest = state.manifest_payload()
    action_id = sorted(manifest.get("actions", {}).keys())[0]
    response = state.run_action(action_id, {})
    assert response["ok"] is True

    payload = state.state_payload()
    records = payload.get("records") or []
    assert records and records[0]["name"] == "Item"
    rows = records[0]["rows"]
    assert [row["id"] for row in rows] == [2, 10]
    fields = records[0]["fields"]
    assert fields == [{"name": "id", "type": "number"}, {"name": "name", "type": "text"}]

    effects = payload.get("effects") or {}
    assert effects.get("action", {}).get("id") == action_id
    changes = effects.get("records") or []
    assert changes and changes[0]["ids"] == [2, 10]
