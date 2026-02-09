from __future__ import annotations

from pathlib import Path
import time

from namel3ss.errors.payload import build_error_payload
from namel3ss.observe import record_event


def record_engine_error(
    project_root: str | Path | None,
    action_id: str,
    actor: dict,
    err: Exception,
    secret_values: list[str] | None,
) -> None:
    if not project_root:
        return
    record_event(
        Path(str(project_root)),
        {
            "type": "engine_error",
            "kind": err.__class__.__name__,
            "message": str(err),
            "action_id": action_id,
            "actor": actor,
            "time": time.time(),
        },
        secret_values=secret_values,
    )


def form_error_payload(errors: list[dict]) -> dict:
    details = {"error_id": "form_validation", "form_errors": errors}
    return build_error_payload("Form validation failed.", kind="runtime", details=details)


__all__ = ["form_error_payload", "record_engine_error"]