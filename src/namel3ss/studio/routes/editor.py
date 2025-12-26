from __future__ import annotations

from typing import Any

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.payload import build_error_from_exception
from namel3ss.studio.editor_api import apply_payload, diagnose_payload, fix_payload, rename_payload


def handle_editor_diagnose(handler: Any, source: str, body: dict) -> None:
    try:
        payload = diagnose_payload(handler.server.app_path, body)  # type: ignore[attr-defined]
        handler._respond_json(payload, status=200)
        return
    except Namel3ssError as err:
        payload = build_error_from_exception(err, kind="editor", source=source)
        handler._respond_json(payload, status=400)
        return


def handle_editor_fix(handler: Any, source: str, body: dict) -> None:
    try:
        payload = fix_payload(handler.server.app_path, body)  # type: ignore[attr-defined]
        handler._respond_json(payload, status=200)
        return
    except Namel3ssError as err:
        payload = build_error_from_exception(err, kind="editor", source=source)
        handler._respond_json(payload, status=400)
        return


def handle_editor_rename(handler: Any, source: str, body: dict) -> None:
    try:
        payload = rename_payload(handler.server.app_path, body)  # type: ignore[attr-defined]
        handler._respond_json(payload, status=200)
        return
    except Namel3ssError as err:
        payload = build_error_from_exception(err, kind="editor", source=source)
        handler._respond_json(payload, status=400)
        return


def handle_editor_apply(handler: Any, source: str, body: dict) -> None:
    try:
        payload = apply_payload(handler.server.app_path, body)  # type: ignore[attr-defined]
        handler._respond_json(payload, status=200)
        return
    except Namel3ssError as err:
        payload = build_error_from_exception(err, kind="editor", source=source)
        handler._respond_json(payload, status=400)
        return


__all__ = [
    "handle_editor_apply",
    "handle_editor_diagnose",
    "handle_editor_fix",
    "handle_editor_rename",
]
