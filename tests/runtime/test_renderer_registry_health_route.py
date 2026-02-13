from __future__ import annotations

import json
import socket
import time
import urllib.request
from pathlib import Path

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.dev_server import BrowserRunner
from namel3ss.runtime.service_runner import ServiceRunner


APP_SOURCE = '''spec is "1.0"

flow "demo":
  return "ok"
'''


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _fetch_json(url: str) -> dict:
    with urllib.request.urlopen(url) as response:
        return json.loads(response.read().decode("utf-8"))


def _wait_for_health(base_url: str, health_path: str) -> None:
    for _ in range(20):
        try:
            payload = _fetch_json(f"{base_url}{health_path}")
        except Exception:
            time.sleep(0.05)
            continue
        if payload.get("ok") is True:
            return
        time.sleep(0.05)
    raise AssertionError("Runtime endpoint did not become healthy.")


def test_browser_runtime_exposes_renderer_registry_health_endpoint(tmp_path: Path) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text(APP_SOURCE, encoding="utf-8")
    runner = BrowserRunner(app_path, mode="run", port=_free_port(), watch_sources=False, headless=True)
    try:
        runner.start(background=True)
        base_url = f"http://127.0.0.1:{runner.bound_port}"
        _wait_for_health(base_url, "/api/health")
        payload = _fetch_json(f"{base_url}/api/renderer-registry/health")
        assert payload["schema_version"] == "renderer_registry_health@1"
        assert isinstance(payload["ok"], bool)
        assert payload["registry"]["status"] in {"validated", "invalid"}
        assert isinstance(payload["parity"]["ok"], bool)
    finally:
        runner.shutdown()


def test_service_runtime_exposes_renderer_registry_health_endpoint(tmp_path: Path) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text(APP_SOURCE, encoding="utf-8")
    runner = ServiceRunner(app_path, "service", port=_free_port(), headless=True)
    try:
        runner.start(background=True)
        base_url = f"http://127.0.0.1:{runner.bound_port}"
        _wait_for_health(base_url, "/health")
        payload = _fetch_json(f"{base_url}/api/renderer-registry/health")
        assert payload["schema_version"] == "renderer_registry_health@1"
        assert isinstance(payload["registry"]["renderer_ids"], list)
        assert isinstance(payload["parity"]["manifest_hash"], str)
    finally:
        runner.shutdown()


def test_browser_runtime_startup_fails_on_renderer_manifest_parity_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text(APP_SOURCE, encoding="utf-8")
    runner = BrowserRunner(app_path, mode="run", port=_free_port(), watch_sources=False)
    monkeypatch.setattr(
        "namel3ss.runtime.server.startup.startup_context.require_renderer_manifest_parity",
        lambda: (_ for _ in ()).throw(Namel3ssError("renderer parity mismatch")),
    )
    try:
        with pytest.raises(Namel3ssError, match="renderer parity mismatch"):
            runner.bind()
    finally:
        runner.shutdown()
