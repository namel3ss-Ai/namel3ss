from __future__ import annotations

from namel3ss.config.loader import load_config
from namel3ss.runtime.preferences.factory import app_pref_key, preference_store_for_app
from namel3ss.runtime.ui.actions import handle_action
from namel3ss.ui.manifest.display_mode import DISPLAY_MODE_STUDIO


def dispatch_ui_action(program_ir, *, action_id: str, payload: dict, ui_mode: str = DISPLAY_MODE_STUDIO) -> dict:
    config = load_config(
        app_path=getattr(program_ir, "app_path", None),
        root=getattr(program_ir, "project_root", None),
    )
    preference = getattr(program_ir, "theme_preference", {}) or {}
    app_path = getattr(program_ir, "app_path", None)
    preference_store = preference_store_for_app(app_path, preference.get("persist"))
    preference_key = app_pref_key(app_path)
    allow_theme_override = bool(preference.get("allow_override", False))
    return handle_action(
        program_ir,
        action_id=action_id,
        payload=payload,
        preference_store=preference_store,
        preference_key=preference_key,
        allow_theme_override=allow_theme_override,
        config=config,
        ui_mode=ui_mode,
    )


__all__ = ["dispatch_ui_action"]
