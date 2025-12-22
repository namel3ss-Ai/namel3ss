from __future__ import annotations

from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir.nodes import lower_program
from namel3ss.parser.core import parse
from namel3ss.runtime.preferences.factory import preference_store_for_app, app_pref_key
from namel3ss.studio.session import SessionState
from namel3ss.ui.manifest import build_manifest


def apply_runtime_theme(source: str, session: SessionState, value: str, app_path: str | None) -> dict:
    ast_program = parse(source)
    program_ir = lower_program(ast_program)
    pref = getattr(program_ir, "theme_preference", {}) or {}
    allow_override = pref.get("allow_override", False)
    persist_mode = pref.get("persist", "none")
    if not allow_override:
        raise Namel3ssError("Theme overrides are disabled. Set app.theme_preference.allow_override is true.")
    session.runtime_theme = value
    preference_store = preference_store_for_app(app_path, persist_mode)
    key = app_pref_key(app_path)
    if persist_mode == "file":
        preference_store.save_theme(key, value)
    manifest = build_manifest(
        program_ir,
        state=session.state,
        store=session.store,
        runtime_theme=value,
        persisted_theme=value if persist_mode == "file" else None,
    )
    return {
        "ok": True,
        "ui": manifest,
        "traces": [{"type": "theme_change", "value": value}],
    }
