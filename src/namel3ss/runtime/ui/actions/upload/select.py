from __future__ import annotations

from typing import Optional

from namel3ss.config.model import AppConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.production_contract import build_run_payload
from namel3ss.runtime.backend.upload_state import apply_upload_selection, upload_state_entry
from namel3ss.runtime.run_pipeline import finalize_run_payload
from namel3ss.runtime.storage.base import Storage
from namel3ss.runtime.ui.actions.validation.validate import ensure_json_serializable
from namel3ss.ui.manifest import build_manifest
from namel3ss.ui.manifest.display_mode import DISPLAY_MODE_STUDIO


def handle_upload_select_action(
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
    ui_mode: str = DISPLAY_MODE_STUDIO,
    diagnostics_enabled: bool = False,
) -> dict:
    upload_name, multiple = _resolve_action_target(action, action_id)
    metadata = _extract_upload_metadata(payload)
    entry = upload_state_entry(metadata)
    apply_upload_selection(state, upload_name=upload_name, entry=entry, multiple=multiple)
    response = build_run_payload(
        ok=True,
        flow_name=None,
        state=state,
        result={"upload": entry, "name": upload_name},
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
        display_mode=ui_mode,
        diagnostics_enabled=diagnostics_enabled,
    )
    ensure_json_serializable(response)
    response = finalize_run_payload(response, secret_values)
    return response


def _resolve_action_target(action: dict, action_id: str) -> tuple[str, bool]:
    name = action.get("name")
    multiple = action.get("multiple")
    if not isinstance(name, str) or not name.strip():
        raise Namel3ssError(_action_name_message(action_id))
    if not isinstance(multiple, bool):
        raise Namel3ssError(_action_multiple_message(action_id))
    return name, multiple


def _extract_upload_metadata(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise Namel3ssError(_payload_type_message())
    if "upload" in payload:
        metadata = payload.get("upload")
    else:
        metadata = payload
    if not isinstance(metadata, dict):
        raise Namel3ssError(_payload_upload_message())
    return metadata


def _action_name_message(action_id: str) -> str:
    return build_guidance_message(
        what=f"Upload action '{action_id}' is missing a name.",
        why="Upload selection actions must declare the target upload name.",
        fix="Use a valid upload name from the UI grammar.",
        example='upload receipt',
    )


def _action_multiple_message(action_id: str) -> str:
    return build_guidance_message(
        what=f"Upload action '{action_id}' has an invalid multiple flag.",
        why="Upload selection actions must declare whether multiple files are allowed.",
        fix="Set multiple to true or false.",
        example="multiple is false",
    )


def _payload_type_message() -> str:
    return build_guidance_message(
        what="Upload selection payload must be an object.",
        why="Upload selection expects an upload metadata object.",
        fix="Send an object with upload metadata.",
        example='{"upload":{"name":"report.pdf","content_type":"application/pdf","bytes":12,"checksum":"..."}}',
    )


def _payload_upload_message() -> str:
    return build_guidance_message(
        what="Upload selection payload is missing upload metadata.",
        why="Upload selection writes metadata into state.",
        fix="Send the upload metadata from /api/upload.",
        example='{"upload":{"name":"report.pdf","content_type":"application/pdf","bytes":12,"checksum":"..."}}',
    )


__all__ = ["handle_upload_select_action"]
