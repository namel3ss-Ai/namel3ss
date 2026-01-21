from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.payload import build_error_from_exception, build_error_payload
from namel3ss.runtime.dev_overlay import build_dev_overlay_payload


def add_dev_overlay(payload: dict, *, mode: str, debug: bool) -> dict:
    if mode == "dev":
        payload["overlay"] = build_dev_overlay_payload(payload, debug=debug)
    return payload


def error_from_exception(
    err: Namel3ssError,
    *,
    kind: str,
    source: dict | None = None,
    mode: str,
    debug: bool,
) -> dict:
    payload = build_error_from_exception(err, kind=kind, source=source)
    return add_dev_overlay(payload, mode=mode, debug=debug)


def error_from_message(
    message: str,
    *,
    kind: str,
    mode: str,
    debug: bool,
) -> dict:
    payload = build_error_payload(message, kind=kind)
    return add_dev_overlay(payload, mode=mode, debug=debug)


__all__ = ["add_dev_overlay", "error_from_exception", "error_from_message"]
