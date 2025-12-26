from __future__ import annotations

from typing import Any

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.payload import build_error_from_exception, build_error_payload
from namel3ss.studio.api import apply_pack_add, apply_pack_disable, apply_pack_enable, apply_pack_verify


def handle_pack_add(handler: Any, source: str, body: dict) -> None:
    if not isinstance(body, dict):
        handler._respond_json(build_error_payload("Body must be a JSON object", kind="packs"), status=400)
        return
    path = body.get("path")
    if not isinstance(path, str) or not path:
        handler._respond_json(build_error_payload("Pack path is required", kind="packs"), status=400)
        return
    try:
        resp = apply_pack_add(handler.server.app_path, path)  # type: ignore[attr-defined]
        status = 200 if resp.get("ok", True) else 400
        handler._respond_json(resp, status=status)
        return
    except Namel3ssError as err:
        payload = build_error_from_exception(err, kind="packs", source=source)
        handler._respond_json(payload, status=400)
        return


def handle_pack_verify(handler: Any, source: str, body: dict) -> None:
    if not isinstance(body, dict):
        handler._respond_json(build_error_payload("Body must be a JSON object", kind="packs"), status=400)
        return
    pack_id = body.get("pack_id")
    if not isinstance(pack_id, str) or not pack_id:
        handler._respond_json(build_error_payload("pack_id is required", kind="packs"), status=400)
        return
    try:
        resp = apply_pack_verify(handler.server.app_path, pack_id)  # type: ignore[attr-defined]
        status = 200 if resp.get("ok", True) else 400
        handler._respond_json(resp, status=status)
        return
    except Namel3ssError as err:
        payload = build_error_from_exception(err, kind="packs", source=source)
        handler._respond_json(payload, status=400)
        return


def handle_pack_enable(handler: Any, source: str, body: dict) -> None:
    if not isinstance(body, dict):
        handler._respond_json(build_error_payload("Body must be a JSON object", kind="packs"), status=400)
        return
    pack_id = body.get("pack_id")
    if not isinstance(pack_id, str) or not pack_id:
        handler._respond_json(build_error_payload("pack_id is required", kind="packs"), status=400)
        return
    try:
        resp = apply_pack_enable(handler.server.app_path, pack_id)  # type: ignore[attr-defined]
        status = 200 if resp.get("ok", True) else 400
        handler._respond_json(resp, status=status)
        return
    except Namel3ssError as err:
        payload = build_error_from_exception(err, kind="packs", source=source)
        handler._respond_json(payload, status=400)
        return


def handle_pack_disable(handler: Any, source: str, body: dict) -> None:
    if not isinstance(body, dict):
        handler._respond_json(build_error_payload("Body must be a JSON object", kind="packs"), status=400)
        return
    pack_id = body.get("pack_id")
    if not isinstance(pack_id, str) or not pack_id:
        handler._respond_json(build_error_payload("pack_id is required", kind="packs"), status=400)
        return
    try:
        resp = apply_pack_disable(handler.server.app_path, pack_id)  # type: ignore[attr-defined]
        status = 200 if resp.get("ok", True) else 400
        handler._respond_json(resp, status=status)
        return
    except Namel3ssError as err:
        payload = build_error_from_exception(err, kind="packs", source=source)
        handler._respond_json(payload, status=400)
        return


__all__ = [
    "handle_pack_add",
    "handle_pack_disable",
    "handle_pack_enable",
    "handle_pack_verify",
]
