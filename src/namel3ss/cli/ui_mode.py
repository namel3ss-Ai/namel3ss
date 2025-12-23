from __future__ import annotations

from namel3ss.config.loader import load_config
from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.identity.context import resolve_identity
from namel3ss.runtime.storage.factory import resolve_store
from namel3ss.runtime.ui.actions import handle_action
from namel3ss.ui.manifest import build_manifest


def render_manifest(program_ir) -> dict:
    config = load_config(
        app_path=getattr(program_ir, "app_path", None),
        root=getattr(program_ir, "project_root", None),
    )
    store = resolve_store(None, config=config)
    identity = resolve_identity(config, getattr(program_ir, "identity", None))
    return build_manifest(program_ir, state={}, store=store, identity=identity)


def run_action(program_ir, action_id: str, payload: dict) -> dict:
    config = load_config(
        app_path=getattr(program_ir, "app_path", None),
        root=getattr(program_ir, "project_root", None),
    )
    store = resolve_store(None, config=config)
    return handle_action(program_ir, action_id=action_id, payload=payload, state={}, store=store, config=config)
