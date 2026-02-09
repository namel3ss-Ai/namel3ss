import json
import socket
import time
import urllib.error
import urllib.request

from namel3ss.runtime.service_runner import ServiceRunner
from namel3ss.runtime.spec_version import NAMEL3SS_SPEC_VERSION, RUNTIME_SPEC_VERSION


APP_SOURCE = '''spec is "1.0"

flow "demo":
  return "ok"
'''


def _fetch_json(url: str, headers: dict[str, str] | None = None) -> dict:
    req = urllib.request.Request(url, method="GET")
    for key, value in (headers or {}).items():
        req.add_header(key, value)
    with urllib.request.urlopen(req) as resp:
        body = resp.read().decode("utf-8")
    return json.loads(body)


def _post_json(url: str, payload: dict, headers: dict[str, str] | None = None) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Content-Length", str(len(data)))
    for key, value in (headers or {}).items():
        req.add_header(key, value)
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


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("0.0.0.0", 0))
        return int(sock.getsockname()[1])


def test_service_runner_health_and_version(tmp_path):
    app = tmp_path / "app.ai"
    app.write_text(APP_SOURCE, encoding="utf-8")
    runner = ServiceRunner(app, "service", build_id="service-test", port=_free_port())
    try:
        runner.start(background=True)
        port = runner.bound_port
        _wait_for_health(port)
        payload = _fetch_json(f"http://127.0.0.1:{port}/health")
        assert payload.get("ok") is True
        assert payload.get("build_id") == "service-test"
        version_payload = _fetch_json(f"http://127.0.0.1:{port}/version")
        assert version_payload.get("version")
    finally:
        runner.shutdown()


def test_service_runner_ui_contract_endpoints(tmp_path):
    app = tmp_path / "app.ai"
    app.write_text(
        'spec is "1.0"\n\n'
        'record "User":\n'
        "  name string\n\n"
        'flow "demo":\n'
        '  return "ok"\n\n'
        'page "home": requires true\n'
        '  form is "User"\n'
        '  button "Run":\n'
        '    calls flow "demo"\n',
        encoding="utf-8",
    )
    runner = ServiceRunner(app, "service", build_id=None, port=_free_port())
    try:
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
    finally:
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
    runner = ServiceRunner(app, "service", build_id=None, port=_free_port())
    try:
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
    finally:
        runner.shutdown()


def test_service_runner_api_first_aliases(tmp_path):
    app = tmp_path / "app.ai"
    app.write_text(
        'spec is "1.0"\n\n'
        'flow "demo":\n'
        "  return \"ok\"\n\n"
        'page "home":\n'
        '  button "Run":\n'
        '    calls flow "demo"\n',
        encoding="utf-8",
    )
    runner = ServiceRunner(app, "service", build_id=None, port=_free_port(), headless=True)
    try:
        runner.start(background=True)
        port = runner.bound_port
        _wait_for_health(port)
        manifest = _fetch_json(f"http://127.0.0.1:{port}/api/ui/manifest")
        assert manifest.get("schema_version") == "1"
        actions = _fetch_json(f"http://127.0.0.1:{port}/api/ui/actions")
        assert actions.get("schema_version") == "1"
        state = _fetch_json(f"http://127.0.0.1:{port}/api/ui/state")
        assert state.get("ok") is True
        assert state.get("api_version") == "1"
        result = _post_json(
            f"http://127.0.0.1:{port}/api/ui/action",
            {"id": "page.home.button.run", "payload": {}},
        )
        assert result.get("ok") is True
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/") as resp:  # noqa: S310
            resp.read()
        raise AssertionError("headless service mode should not serve static root")
    except urllib.error.HTTPError as err:
        assert err.code == 404
    finally:
        runner.shutdown()


def test_service_runner_headless_api_requires_token_and_respects_cors(tmp_path):
    app = tmp_path / "app.ai"
    app.write_text(
        'spec is "1.0"\n\n'
        'flow "demo":\n'
        "  return \"ok\"\n\n"
        'page "home":\n'
        '  button "Run":\n'
        '    calls flow "demo"\n',
        encoding="utf-8",
    )
    runner = ServiceRunner(
        app,
        "service",
        build_id=None,
        port=_free_port(),
        headless=True,
        headless_api_token="test-token",
        headless_cors_origins=("https://frontend.example.com",),
    )
    try:
        runner.start(background=True)
        port = runner.bound_port
        _wait_for_health(port)
        try:
            _fetch_json(f"http://127.0.0.1:{port}/api/v1/ui")
            raise AssertionError("versioned endpoint should require token")
        except urllib.error.HTTPError as err:
            assert err.code == 401
            payload = json.loads(err.read().decode("utf-8"))
            assert payload.get("ok") is False
        headers = {"X-API-Token": "test-token", "Origin": "https://frontend.example.com"}
        payload = _fetch_json(
            f"http://127.0.0.1:{port}/api/v1/ui?include_state=1&include_actions=1",
            headers=headers,
        )
        assert payload.get("ok") is True
        assert payload.get("api_version") == "v1"
        assert payload.get("contract_version") == "runtime-ui@1"
        assert payload.get("spec_version") == NAMEL3SS_SPEC_VERSION
        assert payload.get("runtime_spec_version") == RUNTIME_SPEC_VERSION
        assert isinstance(payload.get("hash"), str) and len(payload["hash"]) == 64
        assert isinstance(payload.get("manifest"), dict)
        assert isinstance(payload.get("actions"), dict)
        action_items = payload["actions"].get("actions")
        assert isinstance(action_items, list) and action_items
        action_id = action_items[0]["id"]
        result = _post_json(
            f"http://127.0.0.1:{port}/api/v1/actions/{action_id}",
            {"args": {}},
            headers=headers,
        )
        assert result.get("ok") is True
        assert result.get("action_id") == action_id
        assert result.get("contract_version") == "runtime-ui@1"
        assert result.get("spec_version") == NAMEL3SS_SPEC_VERSION
        assert result.get("runtime_spec_version") == RUNTIME_SPEC_VERSION
        try:
            _fetch_json(
                f"http://127.0.0.1:{port}/api/v1/ui",
                headers={"X-API-Token": "test-token", "Origin": "https://blocked.example.com"},
            )
            raise AssertionError("versioned endpoint should reject blocked origin")
        except urllib.error.HTTPError as err:
            assert err.code == 403
    finally:
        runner.shutdown()


def test_service_runner_headless_api_upload_selection_updates_state(tmp_path):
    app = tmp_path / "app.ai"
    app.write_text(
        'spec is "1.0"\n\n'
        "capabilities:\n"
        "  uploads\n\n"
        'page "home":\n'
        "  upload receipt\n",
        encoding="utf-8",
    )
    runner = ServiceRunner(
        app,
        "service",
        build_id=None,
        port=_free_port(),
        headless=True,
        headless_api_token="upload-token",
        headless_cors_origins=("https://frontend.example.com",),
    )
    try:
        runner.start(background=True)
        port = runner.bound_port
        _wait_for_health(port)
        headers = {"X-API-Token": "upload-token", "Origin": "https://frontend.example.com"}
        payload = _fetch_json(f"http://127.0.0.1:{port}/api/v1/ui?include_actions=1", headers=headers)
        assert payload.get("ok") is True
        upload_action_id = ""
        for entry in payload.get("actions", {}).get("actions", []):
            if isinstance(entry, dict) and entry.get("type") == "upload_select":
                candidate = entry.get("id")
                if isinstance(candidate, str) and candidate:
                    upload_action_id = candidate
                    break
        if not upload_action_id:
            manifest_actions = payload.get("manifest", {}).get("actions", {})
            for action_id, entry in manifest_actions.items():
                if isinstance(entry, dict) and entry.get("type") == "upload_select":
                    upload_action_id = action_id
                    break
        assert upload_action_id
        response = _post_json(
            f"http://127.0.0.1:{port}/api/v1/actions/{upload_action_id}",
            {
                "args": {
                    "upload": {
                        "name": "receipt.pdf",
                        "content_type": "application/pdf",
                        "bytes": 128,
                        "checksum": "abc123",
                    }
                }
            },
            headers=headers,
        )
        assert response.get("ok") is True
        uploads = response.get("state", {}).get("uploads", {}).get("receipt", {})
        assert "abc123" in uploads
        assert uploads["abc123"]["name"] == "receipt.pdf"
        assert uploads["abc123"]["type"] == "application/pdf"
    finally:
        runner.shutdown()


def test_service_runner_dispatches_timer_trigger(tmp_path):
    app = tmp_path / "app.ai"
    app.write_text(
        'spec is "1.0"\n\n'
        'flow "tick_flow":\n'
        '  return "ok"\n',
        encoding="utf-8",
    )
    (tmp_path / "triggers.yaml").write_text(
        "timer:\n"
        "  - name: nightly_cleanup\n"
        "    cron: 0 0 * * *\n"
        "    flow: tick_flow\n",
        encoding="utf-8",
    )
    runner = ServiceRunner(app, "service", build_id=None, port=_free_port(), headless=True)
    try:
        runner.start(background=True)
        port = runner.bound_port
        _wait_for_health(port)
        observe_path = tmp_path / ".namel3ss" / "observe.jsonl"
        for _ in range(40):
            if observe_path.exists():
                lines = [line for line in observe_path.read_text(encoding="utf-8").splitlines() if line.strip()]
                events = [json.loads(line) for line in lines]
                if any(event.get("type") == "flow_run" and event.get("flow_name") == "tick_flow" for event in events):
                    break
            time.sleep(0.05)
        else:
            raise AssertionError("timer trigger did not dispatch flow in service runtime")
    finally:
        runner.shutdown()


def test_service_runner_dispatches_webhook_trigger(tmp_path):
    app = tmp_path / "app.ai"
    app.write_text(
        'spec is "1.0"\n\n'
        'flow "hook_flow":\n'
        '  return "ok"\n',
        encoding="utf-8",
    )
    (tmp_path / "triggers.yaml").write_text(
        "webhook:\n"
        "  - name: user_signup\n"
        "    path: /hooks/signup\n"
        "    flow: hook_flow\n",
        encoding="utf-8",
    )
    runner = ServiceRunner(app, "service", build_id=None, port=_free_port(), headless=True)
    try:
        runner.start(background=True)
        port = runner.bound_port
        _wait_for_health(port)
        payload = _post_json(f"http://127.0.0.1:{port}/hooks/signup", {"user_id": "u-1"})
        assert payload.get("ok") is True
        assert payload.get("count") == 1
        observe_path = tmp_path / ".namel3ss" / "observe.jsonl"
        for _ in range(40):
            if observe_path.exists():
                lines = [line for line in observe_path.read_text(encoding="utf-8").splitlines() if line.strip()]
                events = [json.loads(line) for line in lines]
                if any(event.get("type") == "flow_run" and event.get("flow_name") == "hook_flow" for event in events):
                    break
            time.sleep(0.05)
        else:
            raise AssertionError("webhook trigger did not dispatch flow in service runtime")
    finally:
        runner.shutdown()


def test_service_runner_dispatches_queue_trigger(tmp_path):
    app = tmp_path / "app.ai"
    app.write_text(
        'spec is "1.0"\n\n'
        'flow "queue_flow":\n'
        '  return "ok"\n',
        encoding="utf-8",
    )
    queue_source = tmp_path / "events" / "queue.jsonl"
    queue_source.parent.mkdir(parents=True, exist_ok=True)
    queue_source.write_text('{"job":"A"}\n', encoding="utf-8")
    (tmp_path / "triggers.yaml").write_text(
        "queue:\n"
        "  - name: jobs\n"
        "    pattern: events/queue.jsonl\n"
        "    flow: queue_flow\n",
        encoding="utf-8",
    )
    runner = ServiceRunner(app, "service", build_id=None, port=_free_port(), headless=True)
    try:
        runner.start(background=True)
        port = runner.bound_port
        _wait_for_health(port)
        observe_path = tmp_path / ".namel3ss" / "observe.jsonl"
        for _ in range(40):
            if observe_path.exists():
                lines = [line for line in observe_path.read_text(encoding="utf-8").splitlines() if line.strip()]
                events = [json.loads(line) for line in lines]
                if any(event.get("type") == "flow_run" and event.get("flow_name") == "queue_flow" for event in events):
                    break
            time.sleep(0.05)
        else:
            raise AssertionError("queue trigger did not dispatch flow in service runtime")
    finally:
        runner.shutdown()


def test_service_runner_dispatches_upload_trigger(tmp_path):
    app = tmp_path / "app.ai"
    app.write_text(
        'spec is "1.0"\n\n'
        'flow "upload_flow":\n'
        '  return "ok"\n',
        encoding="utf-8",
    )
    upload_root = tmp_path / "incoming_uploads"
    upload_root.mkdir(parents=True, exist_ok=True)
    (upload_root / "sample.txt").write_text("payload", encoding="utf-8")
    (tmp_path / "triggers.yaml").write_text(
        "upload:\n"
        "  - name: invoice_upload\n"
        "    directory: incoming_uploads\n"
        "    flow: upload_flow\n",
        encoding="utf-8",
    )
    runner = ServiceRunner(app, "service", build_id=None, port=_free_port(), headless=True)
    try:
        runner.start(background=True)
        port = runner.bound_port
        _wait_for_health(port)
        observe_path = tmp_path / ".namel3ss" / "observe.jsonl"
        for _ in range(40):
            if observe_path.exists():
                lines = [line for line in observe_path.read_text(encoding="utf-8").splitlines() if line.strip()]
                events = [json.loads(line) for line in lines]
                if any(event.get("type") == "flow_run" and event.get("flow_name") == "upload_flow" for event in events):
                    break
            time.sleep(0.05)
        else:
            raise AssertionError("upload trigger did not dispatch flow in service runtime")
    finally:
        runner.shutdown()
