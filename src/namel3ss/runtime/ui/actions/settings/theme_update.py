from __future__ import annotations

from typing import Optional

from namel3ss.config.model import AppConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.production_contract import build_run_payload
from namel3ss.runtime.run_pipeline import finalize_run_payload
from namel3ss.runtime.storage.base import Storage
from namel3ss.runtime.ui.actions.validation.validate import ensure_json_serializable
from namel3ss.ui.manifest import build_manifest
from namel3ss.ui.manifest.display_mode import DISPLAY_MODE_STUDIO
from namel3ss.ui.theme_tokens import UI_THEME_TOKEN_ORDER, normalize_ui_theme_token_value


def handle_theme_settings_update_action(
    program_ir,
    *,
    action_id: str,
    action: dict,
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
    del action
    settings = _parse_settings(payload)
    _apply_settings(state, settings)
    response = build_run_payload(
        ok=True,
        flow_name=None,
        state=state,
        result={"updated": list(settings.keys())},
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


def _parse_settings(payload: dict) -> dict[str, str]:
    if not isinstance(payload, dict):
        raise Namel3ssError("Theme settings payload must be an object.")
    settings = payload.get("settings")
    if not isinstance(settings, dict):
        raise Namel3ssError("Theme settings payload must include settings object.")
    normalized: dict[str, str] = {}
    for key, value in settings.items():
        if key not in UI_THEME_TOKEN_ORDER:
            raise Namel3ssError(f"Unknown theme setting '{key}'.")
        normalized[key] = normalize_ui_theme_token_value(key, value)
    if not normalized:
        raise Namel3ssError("Theme settings payload must include at least one setting.")
    return normalized


def _apply_settings(state: dict, settings: dict[str, str]) -> None:
    ui = state.get("ui")
    if not isinstance(ui, dict):
        ui = {}
        state["ui"] = ui
    current = ui.get("settings")
    if not isinstance(current, dict):
        current = {}
        ui["settings"] = current
    for key, value in settings.items():
        current[key] = value


__all__ = ["handle_theme_settings_update_action"]
