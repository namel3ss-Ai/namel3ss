from __future__ import annotations

from typing import Any

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.payload import build_error_from_exception, build_error_payload
from namel3ss.studio.registry_api import apply_discover, apply_pack_install, apply_registry_add_bundle


def handle_registry_add(handler: Any, source: str, body: dict) -> None:
    if not isinstance(body, dict):
        handler._respond_json(build_error_payload("Body must be a JSON object", kind="registry"), status=400)
        return
    path = body.get("path")
    if not isinstance(path, str) or not path:
        handler._respond_json(build_error_payload("path is required", kind="registry"), status=400)
        return
    try:
        resp = apply_registry_add_bundle(handler.server.app_path, path)  # type: ignore[attr-defined]
        status = 200 if resp.get("ok", True) else 400
        handler._respond_json(resp, status=status)
        return
    except Namel3ssError as err:
        payload = build_error_from_exception(err, kind="registry", source=source)
        handler._respond_json(payload, status=400)
        return


def handle_discover(handler: Any, source: str, body: dict) -> None:
    if not isinstance(body, dict):
        handler._respond_json(build_error_payload("Body must be a JSON object", kind="registry"), status=400)
        return
    try:
        resp = apply_discover(handler.server.app_path, body)  # type: ignore[attr-defined]
        status = 200 if resp.get("ok", True) else 400
        handler._respond_json(resp, status=status)
        return
    except Namel3ssError as err:
        payload = build_error_from_exception(err, kind="registry", source=source)
        handler._respond_json(payload, status=400)
        return


def handle_pack_install(handler: Any, source: str, body: dict) -> None:
    if not isinstance(body, dict):
        handler._respond_json(build_error_payload("Body must be a JSON object", kind="packs"), status=400)
        return
    try:
        resp = apply_pack_install(handler.server.app_path, body)  # type: ignore[attr-defined]
        status = 200 if resp.get("ok", True) else 400
        handler._respond_json(resp, status=status)
        return
    except Namel3ssError as err:
        payload = build_error_from_exception(err, kind="packs", source=source)
        handler._respond_json(payload, status=400)
        return


__all__ = ["handle_discover", "handle_pack_install", "handle_registry_add"]
