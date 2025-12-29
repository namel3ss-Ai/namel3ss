from __future__ import annotations

from pathlib import Path

from namel3ss.config.loader import load_config
from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.storage.factory import resolve_store
from namel3ss.runtime.ui.actions import handle_action
from namel3ss.ui.export.contract import build_contract_manifest, build_ui_contract_payload
from namel3ss.ui.export.writer import write_ui_exports


def render_manifest(program_ir) -> dict:
    return build_contract_manifest(program_ir)


def run_action(program_ir, action_id: str, payload: dict) -> dict:
    config = load_config(
        app_path=getattr(program_ir, "app_path", None),
        root=getattr(program_ir, "project_root", None),
    )
    store = resolve_store(None, config=config)
    return handle_action(program_ir, action_id=action_id, payload=payload, state={}, store=store, config=config)


def export_ui_contract(program_ir) -> dict:
    payload = build_ui_contract_payload(program_ir)
    project_root = _resolve_project_root(program_ir)
    return write_ui_exports(
        project_root,
        ui=payload["ui"],
        actions=payload["actions"],
        schema=payload["schema"],
    )


def _resolve_project_root(program_ir) -> Path:
    project_root = getattr(program_ir, "project_root", None)
    if project_root:
        return Path(project_root)
    app_path = getattr(program_ir, "app_path", None)
    if app_path:
        return Path(app_path).resolve().parent
    raise Namel3ssError("Project root is required to export UI contract")
