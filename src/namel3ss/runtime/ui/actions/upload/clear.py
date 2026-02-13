from __future__ import annotations

from typing import Optional

from namel3ss.config.model import AppConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.production_contract import build_run_payload
from namel3ss.runtime.backend.upload_state import clear_upload_selection
from namel3ss.runtime.run_pipeline import finalize_run_payload
from namel3ss.runtime.storage.base import Storage
from namel3ss.runtime.ui.actions.validation.validate import ensure_json_serializable
from namel3ss.ui.manifest import build_manifest


def handle_upload_clear_action(
    program_ir,
    *,
    action: dict,
    action_id: str,
    payload: dict,
    state: dict,
    store: Storage,
    runtime_theme: Optional[str],
    config: AppConfig | None = None,
    identity: dict | None = None,
    auth_context: object | None = None,
    secret_values: list[str] | None = None,
) -> dict:
    upload_name = _resolve_action_target(action, action_id)
    upload_id = _extract_upload_id(payload)
    clear_upload_selection(state, upload_name=upload_name, upload_id=upload_id)
    response = build_run_payload(
        ok=True,
        flow_name=None,
        state=state,
        result={"upload_clear": {"name": upload_name, "upload_id": upload_id}},
        traces=[],
        project_root=getattr(program_ir, "project_root", None),
    )
    response["ui"] = build_manifest(
        program_ir,
        config=config,
        state=state,
        store=store,
        runtime_theme=runtime_theme,
        identity=identity,
        auth_context=auth_context,
    )
    ensure_json_serializable(response)
    response = finalize_run_payload(response, secret_values)
    return response


def _resolve_action_target(action: dict, action_id: str) -> str:
    name = action.get("name")
    if not isinstance(name, str) or not name.strip():
        raise Namel3ssError(_action_name_message(action_id))
    return name.strip()


def _extract_upload_id(payload: dict) -> str | None:
    if not isinstance(payload, dict):
        raise Namel3ssError(_payload_type_message())
    upload_id = payload.get("upload_id")
    if upload_id is None:
        return None
    if not isinstance(upload_id, str) or not upload_id.strip():
        raise Namel3ssError(_upload_id_message())
    return upload_id.strip()


def _action_name_message(action_id: str) -> str:
    return build_guidance_message(
        what=f"Upload clear action '{action_id}' is missing a name.",
        why="Upload clear actions must declare the target upload name.",
        fix="Use a valid upload name from the UI grammar.",
        example="upload receipt",
    )


def _payload_type_message() -> str:
    return build_guidance_message(
        what="Upload clear payload must be an object.",
        why="Upload clear actions optionally accept upload_id.",
        fix='Send {} or {"upload_id":"<checksum>"}.',
        example='{"upload_id":"<checksum>"}',
    )


def _upload_id_message() -> str:
    return build_guidance_message(
        what="Upload clear payload contains an invalid upload_id.",
        why="Upload clear uses upload_id to remove a single selected file.",
        fix="Provide a non-empty upload id string or omit it to clear all files.",
        example='{"upload_id":"<checksum>"}',
    )


__all__ = ["handle_upload_clear_action"]
