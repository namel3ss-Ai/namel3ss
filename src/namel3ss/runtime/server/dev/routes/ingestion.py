from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from urllib.parse import parse_qs

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.payload import build_error_payload
from namel3ss.runtime.backend.upload_handler import handle_upload, handle_upload_list
from namel3ss.runtime.backend.upload_recorder import UploadRecorder, apply_upload_error_payload
from namel3ss.runtime.server.dev.errors import error_from_exception, error_from_message


def handle_uploads_get(handler: Any, path: str) -> bool:
    if path != "/api/uploads":
        return False
    response, status = handle_upload_list_get(handler)
    handler._respond_json(response, status=status)
    return True


def handle_upload_post(handler: Any, query: str) -> tuple[dict, int]:
    state = handler._state()
    state._refresh_if_needed()
    program = state.program
    if program is None:
        payload = build_error_payload("Program not loaded.", kind="engine")
        return payload, 500
    upload_name = handler.headers.get("X-Upload-Name")
    if not upload_name:
        params = parse_qs(query or "")
        name_values = params.get("name") or []
        upload_name = name_values[0] if name_values else None
    length_header = handler.headers.get("Content-Length")
    content_length = None
    if length_header:
        try:
            content_length = int(length_header)
        except ValueError:
            content_length = None
    ctx = SimpleNamespace(
        capabilities=getattr(program, "capabilities", ()),
        project_root=getattr(program, "project_root", None),
        app_path=getattr(program, "app_path", None),
    )
    recorder = UploadRecorder()
    try:
        response = handle_upload(
            ctx,
            headers=dict(handler.headers.items()),
            rfile=handler.rfile,
            content_length=content_length,
            upload_name=upload_name,
            recorder=recorder,
        )
        return response, 200
    except Namel3ssError as err:
        payload = error_from_exception(
            err,
            kind="engine",
            source=handler._source_payload(),
            mode=handler._mode(),
            debug=handler._state().debug,
        )
        payload = apply_upload_error_payload(payload, recorder)
        return payload, 400
    except Exception as err:  # pragma: no cover - defensive guard
        payload = error_from_message(
            str(err),
            kind="internal",
            mode=handler._mode(),
            debug=handler._state().debug,
        )
        payload = apply_upload_error_payload(payload, recorder)
        return payload, 500


def handle_upload_list_get(handler: Any) -> tuple[dict, int]:
    state = handler._state()
    state._refresh_if_needed()
    program = state.program
    if program is None:
        payload = build_error_payload("Program not loaded.", kind="engine")
        return payload, 500
    ctx = SimpleNamespace(
        capabilities=getattr(program, "capabilities", ()),
        project_root=getattr(program, "project_root", None),
        app_path=getattr(program, "app_path", None),
    )
    try:
        response = handle_upload_list(ctx)
        return response, 200
    except Namel3ssError as err:
        payload = error_from_exception(
            err,
            kind="engine",
            source=handler._source_payload(),
            mode=handler._mode(),
            debug=handler._state().debug,
        )
        return payload, 400
    except Exception as err:  # pragma: no cover - defensive guard
        payload = error_from_message(
            str(err),
            kind="internal",
            mode=handler._mode(),
            debug=handler._state().debug,
        )
        return payload, 500


__all__ = ["handle_upload_post", "handle_uploads_get"]
