import json
import time
import urllib.request

from namel3ss.runtime.service_runner import ServiceRunner


APP_SOURCE = '''spec is "1.0"

flow "demo":
  return "ok"
'''


def _fetch_json(url: str) -> dict:
    with urllib.request.urlopen(url) as resp:
        body = resp.read().decode("utf-8")
    return json.loads(body)


def _post_json(url: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Content-Length", str(len(data)))
    with urllib.request.urlopen(req) as resp:
        body = resp.read().decode("utf-8")
    return json.loads(body)


def _wait_for_health(port: int) -> None:
    for _ in range(10):
        try:
            payload = _fetch_json(f"http://127.0.0.1:{port}/health")
            if payload.get("ok") is True:
                return
        except Exception:
            time.sleep(0.05)
    raise AssertionError("Service runner not ready")


def test_service_runner_health_and_version(tmp_path):
    app = tmp_path / "app.ai"
    app.write_text(APP_SOURCE, encoding="utf-8")
    runner = ServiceRunner(app, "service", build_id="service-test", port=0)
    runner.start(background=True)
    port = runner.bound_port
    _wait_for_health(port)
    payload = _fetch_json(f"http://127.0.0.1:{port}/health")
    assert payload.get("ok") is True
    assert payload.get("build_id") == "service-test"
    version_payload = _fetch_json(f"http://127.0.0.1:{port}/version")
    assert version_payload.get("version")
    runner.shutdown()


def test_service_runner_ui_contract_endpoints(tmp_path):
    app = tmp_path / "app.ai"
    app.write_text(
        'spec is "1.0"\n\n'
        'record "User":\n'
        "  name string\n\n"
        'flow "demo":\n'
        '  return "ok"\n\n'
        'page "home":\n'
        '  form is "User"\n'
        '  button "Run":\n'
        '    calls flow "demo"\n',
        encoding="utf-8",
    )
    runner = ServiceRunner(app, "service", build_id=None, port=0)
    runner.start(background=True)
    port = runner.bound_port
    _wait_for_health(port)
    contract = _fetch_json(f"http://127.0.0.1:{port}/api/ui/contract")
    assert contract["ui"]["schema_version"] == "1"
    assert contract["actions"]["schema_version"] == "1"
    assert contract["schema"]["schema_version"] == "1"
    ui_only = _fetch_json(f"http://127.0.0.1:{port}/api/ui/contract/ui")
    assert ui_only["schema_version"] == "1"
    actions_only = _fetch_json(f"http://127.0.0.1:{port}/api/ui/contract/actions")
    action_ids = [item["id"] for item in actions_only.get("actions", [])]
    assert "page.home.form.user" in action_ids
    schema_only = _fetch_json(f"http://127.0.0.1:{port}/api/ui/contract/schema")
    record_names = [item["name"] for item in schema_only.get("records", [])]
    assert "User" in record_names
    runner.shutdown()


def test_service_runner_mixed_ui_static_and_action(tmp_path):
    app = tmp_path / "app.ai"
    app.write_text(
        'spec is "1.0"\n\n'
        'flow "echo":\n'
        "  return input.message\n\n"
        'page "home":\n'
        '  button "Send":\n'
        '    calls flow "echo"\n',
        encoding="utf-8",
    )
    ui_root = tmp_path / "ui"
    ui_root.mkdir()
    (ui_root / "index.html").write_text("<html>external ui</html>", encoding="utf-8")
    runner = ServiceRunner(app, "service", build_id=None, port=0)
    runner.start(background=True)
    port = runner.bound_port
    _wait_for_health(port)
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/") as resp:
        body = resp.read().decode("utf-8")
    assert "external ui" in body
    response = _post_json(
        f"http://127.0.0.1:{port}/api/action",
        {"id": "page.home.button.send", "payload": {"message": "hi"}},
    )
    assert response.get("ok") is True
    assert response.get("result") == "hi"
    runner.shutdown()
