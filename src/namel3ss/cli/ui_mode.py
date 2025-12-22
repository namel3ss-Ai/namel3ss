from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.storage.factory import resolve_store
from namel3ss.runtime.ui.actions import handle_action
from namel3ss.ui.manifest import build_manifest


def render_manifest(program_ir) -> dict:
    return build_manifest(program_ir, state={}, store=resolve_store(None))


def run_action(program_ir, action_id: str, payload: dict) -> dict:
    return handle_action(program_ir, action_id=action_id, payload=payload, state={}, store=resolve_store(None))
