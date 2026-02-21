from __future__ import annotations

import socket

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.dev_server import BrowserRunner


APP_SOURCE = '''spec is "1.0"

flow "demo":
  return "ok"
'''


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def test_browser_runner_rejects_lock_collision(tmp_path) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text(APP_SOURCE, encoding="utf-8")
    port = _free_port()
    runner_one = BrowserRunner(app_path, mode="run", port=port, watch_sources=False, headless=True)
    runner_one.start(background=True)
    runner_two = BrowserRunner(app_path, mode="run", port=port, watch_sources=False, headless=True)
    try:
        with pytest.raises(Namel3ssError) as exc:
            runner_two.bind()
        assert "Runtime already running" in str(exc.value)
    finally:
        runner_two.shutdown()
        runner_one.shutdown()


def test_browser_runner_emits_startup_banner(tmp_path, capsys) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text(APP_SOURCE, encoding="utf-8")
    runner = BrowserRunner(app_path, mode="run", port=_free_port(), watch_sources=False, headless=True)
    try:
        runner.start(background=True)
        output = capsys.readouterr().out
        assert "Runtime startup " in output
        assert "manifest_hash" in output
        assert "renderer_registry_hash" in output
    finally:
        runner.shutdown()


def test_browser_runner_fails_startup_on_manifest_hash_drift(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text(APP_SOURCE, encoding="utf-8")
    runner = BrowserRunner(app_path, mode="run", port=_free_port(), watch_sources=False, headless=True)
    monkeypatch.setattr(
        "namel3ss.runtime.server.dev.app.require_static_runtime_manifest_parity",
        lambda **_: (_ for _ in ()).throw(Namel3ssError("manifest drift")),
    )
    try:
        with pytest.raises(Namel3ssError, match="manifest drift"):
            runner.bind()
    finally:
        runner.shutdown()
