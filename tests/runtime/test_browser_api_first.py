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


def _fetch_json(url: str) -> dict:
    with urllib.request.urlopen(url) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _post_json(url: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Content-Length", str(len(data)))
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
