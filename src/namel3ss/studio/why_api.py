from __future__ import annotations

from pathlib import Path

from namel3ss.cli.explain_mode import build_explain_payload
from namel3ss.errors.payload import build_error_payload


def get_why_payload(app_path: str) -> dict:
    app_file = Path(app_path)
    payload = build_explain_payload(app_file)
    return payload if isinstance(payload, dict) else build_error_payload("Explain payload invalid", kind="internal")


__all__ = ["get_why_payload"]
