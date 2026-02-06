from __future__ import annotations

import json
import socket
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from namel3ss.runtime.dev_server import BrowserRunner
from namel3ss.runtime.service_runner import ServiceRunner


APP_SOURCE = '''spec is "1.0"

flow "echo":
  return input.message

page "home":
  button "Send":
    calls flow "echo"
'''

SCALABLE_APP_SOURCE = '''spec is "1.0"

capabilities:
  performance_scalability

flow "echo":
  return input.message

page "home":
  button "Send":
    calls flow "echo"
'''


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


def _wait_for_health(url: str) -> None:
    for _ in range(20):
        try:
            payload = _fetch_json(url)
            if payload.get("ok") is True:
                return
        except Exception:
            time.sleep(0.05)
    raise AssertionError("Server did not become healthy")


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def test_browser_runner_exposes_concurrency_settings(tmp_path: Path) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text(APP_SOURCE, encoding="utf-8")
    (tmp_path / "concurrency.yaml").write_text(
        "server_mode: threaded\nmax_threads: 2\nworker_processes: 2\n",
        encoding="utf-8",
    )
    runner = BrowserRunner(app_path, mode="run", port=_free_port(), watch_sources=False)
    try:
        runner.start(background=True)
        health_url = f"http://127.0.0.1:{runner.bound_port}/api/health"
        _wait_for_health(health_url)
        payload = _fetch_json(health_url)
        concurrency = payload.get("concurrency") or {}
        assert concurrency.get("server_mode") == "threaded"
        assert concurrency.get("max_threads") == 2
        assert getattr(runner.server, "max_threads", None) == 2
    finally:
        runner.shutdown()


def test_service_runner_handles_parallel_health_requests(tmp_path: Path) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text(APP_SOURCE, encoding="utf-8")
    (tmp_path / "concurrency.yaml").write_text(
        "server_mode: threaded\nmax_threads: 4\nworker_processes: 2\n",
        encoding="utf-8",
    )
    runner = ServiceRunner(app_path, "service", build_id="scale-test", port=_free_port())
    try:
        runner.start(background=True)
        health_url = f"http://127.0.0.1:{runner.bound_port}/health"
        _wait_for_health(health_url)
        with ThreadPoolExecutor(max_workers=8) as pool:
            rows = list(pool.map(lambda _: _fetch_json(health_url), range(16)))
        assert all(item.get("ok") is True for item in rows)
        assert rows[0].get("concurrency", {}).get("max_threads") == 4
    finally:
        runner.shutdown()


def test_service_runner_uses_worker_pool_when_scalability_capability_enabled(tmp_path: Path) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text(SCALABLE_APP_SOURCE, encoding="utf-8")
    (tmp_path / "concurrency.yaml").write_text(
        "server_mode: threaded\nmax_threads: 2\nworker_processes: 2\n",
        encoding="utf-8",
    )
    runner = ServiceRunner(app_path, "service", build_id="scale-workers", port=_free_port())
    try:
        runner.start(background=True)
        base = f"http://127.0.0.1:{runner.bound_port}"
        _wait_for_health(f"{base}/health")

        health = _fetch_json(f"{base}/health")
        assert health.get("process_model") == "worker_pool:2"

        actions = _fetch_json(f"{base}/api/ui/actions")
        action_id = actions["actions"][0]["id"]
        result = _post_json(f"{base}/api/action", {"id": action_id, "payload": {"message": "hello"}})
        assert result["ok"] is True
        assert result["process_model"] == "worker_pool"
    finally:
        runner.shutdown()
