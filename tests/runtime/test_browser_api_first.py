from __future__ import annotations

import json
import socket
import time
import urllib.error
import urllib.request
from pathlib import Path

from namel3ss.runtime.dev_server import BrowserRunner


APP_SOURCE = '''spec is "1.0"

flow "increment":
  set state.counter is 1
  return state.counter

page "home":
  button "Run":
    calls flow "increment"
'''


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _fetch_json(url: str, headers: dict[str, str] | None = None) -> dict:
    req = urllib.request.Request(url, method="GET")
    for key, value in (headers or {}).items():
        req.add_header(key, value)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _fetch_text(url: str) -> str:
    with urllib.request.urlopen(url) as resp:
        return resp.read().decode("utf-8")


def _fetch_text_with_status(
    url: str,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, str], str]:
    req = urllib.request.Request(url, method="GET")
    for key, value in (headers or {}).items():
        req.add_header(key, value)
    try:
        with urllib.request.urlopen(req) as resp:
            body = resp.read().decode("utf-8")
            return int(getattr(resp, "status", 200)), dict(resp.headers.items()), body
    except urllib.error.HTTPError as err:
        return err.code, dict(err.headers.items()), err.read().decode("utf-8")


def _post_json(url: str, payload: dict, headers: dict[str, str] | None = None) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Content-Length", str(len(data)))
    for key, value in (headers or {}).items():
        req.add_header(key, value)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _wait_ready(base_url: str) -> None:
    for _ in range(20):
        try:
            payload = _fetch_json(f"{base_url}/api/health")
            if payload.get("ok") is True:
                return
        except Exception:
            time.sleep(0.05)
    raise AssertionError("Runtime not ready")


def test_headless_browser_runner_exposes_api_first_endpoints(tmp_path: Path) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text(APP_SOURCE, encoding="utf-8")

    runner = BrowserRunner(app_path, mode="run", port=_free_port(), watch_sources=False, headless=True)
    try:
        runner.start(background=True)
        base_url = f"http://127.0.0.1:{runner.bound_port}"
        _wait_ready(base_url)

        manifest = _fetch_json(f"{base_url}/api/ui/manifest")
        assert manifest["ok"] is True
        assert manifest["manifest"]["pages"]

        actions = _fetch_json(f"{base_url}/api/ui/actions")
        assert actions["ok"] is True
        action_id = actions["actions"][0]["id"]

        state_before = _fetch_json(f"{base_url}/api/ui/state")
        assert state_before["ok"] is True
        assert state_before["state"]["values"] == {}

        action_result = _post_json(f"{base_url}/api/ui/action", {"id": action_id, "payload": {}})
        assert action_result["ok"] is True
        assert action_result["success"] is True
        assert action_result["new_state"]["counter"] == 1

        state_after = _fetch_json(f"{base_url}/api/ui/state")
        assert state_after["state"]["values"]["counter"] == 1

        with urllib.request.urlopen(f"{base_url}/api/health") as resp:
            health = json.loads(resp.read().decode("utf-8"))
        assert health["headless"] is True

        try:
            urllib.request.urlopen(f"{base_url}/")
            raise AssertionError("Headless mode should not serve static UI")
        except urllib.error.HTTPError as err:
            assert err.code == 404
    finally:
        runner.shutdown()


def test_headless_browser_runner_versioned_api_requires_token(tmp_path: Path) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text(APP_SOURCE, encoding="utf-8")

    runner = BrowserRunner(
        app_path,
        mode="run",
        port=_free_port(),
        watch_sources=False,
        headless=True,
        headless_api_token="token-123",
        headless_cors_origins=("https://frontend.example.com",),
    )
    try:
        runner.start(background=True)
        base_url = f"http://127.0.0.1:{runner.bound_port}"
        _wait_ready(base_url)

        try:
            _fetch_json(f"{base_url}/api/v1/ui")
            raise AssertionError("versioned endpoint should require token")
        except urllib.error.HTTPError as err:
            assert err.code == 401

        headers = {"X-API-Token": "token-123", "Origin": "https://frontend.example.com"}
        payload = _fetch_json(f"{base_url}/api/v1/ui?include_actions=1", headers=headers)
        assert payload["ok"] is True
        assert payload["api_version"] == "v1"
        assert isinstance(payload.get("manifest"), dict)
        assert isinstance(payload.get("hash"), str) and len(payload["hash"]) == 64
        actions = payload.get("actions")
        assert isinstance(actions, dict)
        action_id = actions["actions"][0]["id"]

        result = _post_json(f"{base_url}/api/v1/actions/{action_id}", {"args": {}}, headers=headers)
        assert result["ok"] is True
        assert result["action_id"] == action_id

        status, response_headers, _ = _fetch_text_with_status(f"{base_url}/api/v1/ui", headers=headers)
        assert status == 200
        etag = response_headers.get("ETag", "")
        assert etag.startswith('"sha256-')
        assert response_headers.get("Cache-Control") == "private, max-age=0, must-revalidate"

        not_modified_headers = dict(headers)
        not_modified_headers["If-None-Match"] = etag
        status, response_headers, body = _fetch_text_with_status(f"{base_url}/api/v1/ui", headers=not_modified_headers)
        assert status == 304
        assert response_headers.get("ETag") == etag
        assert body == ""
    finally:
        runner.shutdown()


def test_browser_runner_serves_plugin_assets(tmp_path: Path) -> None:
    plugin_root = tmp_path / "ui_plugins" / "demo_widget"
    plugin_root.mkdir(parents=True)
    assets_dir = plugin_root / "assets"
    assets_dir.mkdir()
    (assets_dir / "runtime.js").write_text("window.demoWidget = true;\n", encoding="utf-8")
    (assets_dir / "style.css").write_text(".demo-widget { color: #111; }\n", encoding="utf-8")
    (plugin_root / "renderer.py").write_text(
        "def render(props, state):\n"
        "    return [{\"type\": \"text\", \"text\": \"ok\"}]\n",
        encoding="utf-8",
    )
    (plugin_root / "plugin.json").write_text(
        "{\n"
        '  "name": "demo_widget",\n'
        '  "module": "renderer.py",\n'
        '  "asset_js": "assets/runtime.js",\n'
        '  "asset_css": "assets/style.css",\n'
        '  "components": [{"name": "DemoWidget", "props": {}}]\n'
        "}\n",
        encoding="utf-8",
    )
    app_path = tmp_path / "app.ai"
    app_path.write_text(
        'spec is "1.0"\n\n'
        "capabilities:\n"
        "  custom_ui\n"
        "  sandbox\n\n"
        'use plugin "demo_widget"\n\n'
        'page "home":\n'
        "  DemoWidget\n",
        encoding="utf-8",
    )
    runner = BrowserRunner(app_path, mode="run", port=_free_port(), watch_sources=False, headless=True)
    try:
        runner.start(background=True)
        base_url = f"http://127.0.0.1:{runner.bound_port}"
        _wait_ready(base_url)
        js_status, js_headers, js = _fetch_text_with_status(f"{base_url}/api/plugins/demo_widget/assets/js/assets/runtime.js")
        css_status, css_headers, css = _fetch_text_with_status(f"{base_url}/api/plugins/demo_widget/assets/css/assets/style.css")
        assert js_status == 200
        assert css_status == 200
        assert js_headers.get("Cache-Control") == "public, max-age=31536000, immutable"
        assert css_headers.get("Cache-Control") == "public, max-age=31536000, immutable"
        assert js_headers.get("ETag", "").startswith('"sha256-')
        assert css_headers.get("ETag", "").startswith('"sha256-')
        assert "demoWidget" in js
        assert ".demo-widget" in css

        not_modified = {"If-None-Match": js_headers["ETag"]}
        status, response_headers, body = _fetch_text_with_status(
            f"{base_url}/api/plugins/demo_widget/assets/js/assets/runtime.js",
            headers=not_modified,
        )
        assert status == 304
        assert response_headers.get("ETag") == js_headers["ETag"]
        assert body == ""
    finally:
        runner.shutdown()
