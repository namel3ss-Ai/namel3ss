from __future__ import annotations

import threading

from namel3ss.runtime.security.retention_enforcer import enforce_retention_policies


DEFAULT_RETENTION_INTERVAL_SECONDS = 60


def run_retention_loop(
    *,
    stop_event: threading.Event,
    program_state,
    interval_seconds: int | float = DEFAULT_RETENTION_INTERVAL_SECONDS,
) -> None:
    interval = max(0.05, float(interval_seconds))
    while not stop_event.wait(float(interval)):
        try:
            if program_state is None:
                continue
            if program_state.refresh_if_needed():
                pass
            program = program_state.program
            if program is None:
                continue
            enforce_retention_policies(
                getattr(program, "project_root", None),
                getattr(program, "app_path", None),
            )
        except Exception:
            # Retention enforcement is best-effort during runtime.
            # Errors are surfaced through explicit CLI commands and tests.
            continue


__all__ = ["DEFAULT_RETENTION_INTERVAL_SECONDS", "run_retention_loop"]
