from __future__ import annotations

from pathlib import Path

from namel3ss.cli.why_mode import build_why_payload
from namel3ss.config.loader import load_config
from namel3ss.errors.payload import build_error_payload
from namel3ss.secrets import collect_secret_values, redact_payload


def get_why_payload(app_path: str) -> dict:
    app_file = Path(app_path)
    project_root = app_file.parent
    payload = build_why_payload(app_file)
    config = load_config(app_path=app_file, root=project_root)
    redacted = redact_payload(payload, collect_secret_values(config))
    if isinstance(redacted, dict):
        return redacted
    return build_error_payload("Why payload invalid", kind="internal")


__all__ = ["get_why_payload"]
