from __future__ import annotations

import threading

import namel3ss.runtime.security.retention_loop as retention_loop_module


class _ProgramState:
    def __init__(self, project_root, app_path) -> None:
        self.program = type("Program", (), {"project_root": project_root, "app_path": app_path})()

    def refresh_if_needed(self) -> bool:
        return False


def test_retention_loop_runs_enforcer(monkeypatch, tmp_path) -> None:
    calls: list[tuple[object, object]] = []
    stop_event = threading.Event()

    def _fake_enforce(project_root, app_path):
        calls.append((project_root, app_path))
        stop_event.set()
        return {"ok": True}

    monkeypatch.setattr(retention_loop_module, "enforce_retention_policies", _fake_enforce)
    state = _ProgramState(tmp_path, tmp_path / "app.ai")
    thread = threading.Thread(
        target=retention_loop_module.run_retention_loop,
        kwargs={"stop_event": stop_event, "program_state": state, "interval_seconds": 0.05},
        daemon=True,
    )
    thread.start()
    thread.join(timeout=1.0)
    assert calls == [(tmp_path, tmp_path / "app.ai")]

