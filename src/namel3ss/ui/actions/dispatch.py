from __future__ import annotations

from namel3ss.config.loader import load_config
from namel3ss.runtime.audit.runtime_capture import attach_audit_artifacts
from namel3ss.runtime.errors.normalize import attach_runtime_error_payload
from namel3ss.runtime.providers.guardrails import provider_guardrail_diagnostics
from namel3ss.runtime.preferences.factory import app_pref_key, preference_store_for_app
from namel3ss.runtime.ui.actions import handle_action
from namel3ss.ui.manifest.elements.audit_viewer import inject_audit_viewer_elements
from namel3ss.ui.manifest.elements.retrieval_explain import inject_retrieval_explain_elements
from namel3ss.ui.manifest.elements.runtime_error import inject_runtime_error_elements
from namel3ss.ui.manifest.display_mode import DISPLAY_MODE_STUDIO


def dispatch_ui_action(
    program_ir,
    *,
    action_id: str,
    payload: dict,
    ui_mode: str = DISPLAY_MODE_STUDIO,
    diagnostics_enabled: bool = False,
) -> dict:
    config = load_config(
        app_path=getattr(program_ir, "app_path", None),
        root=getattr(program_ir, "project_root", None),
    )
    preference = getattr(program_ir, "theme_preference", {}) or {}
    app_path = getattr(program_ir, "app_path", None)
    preference_store = preference_store_for_app(app_path, preference.get("persist"))
    preference_key = app_pref_key(app_path)
    allow_theme_override = bool(preference.get("allow_override", False))
    response = handle_action(
        program_ir,
        action_id=action_id,
        payload=payload,
        preference_store=preference_store,
        preference_key=preference_key,
        allow_theme_override=allow_theme_override,
        config=config,
        raise_on_error=False,
        ui_mode=ui_mode,
        diagnostics_enabled=diagnostics_enabled,
    )
    diagnostics = provider_guardrail_diagnostics(config)
    response = attach_runtime_error_payload(response, endpoint="/api/action", diagnostics=diagnostics)
    response = attach_audit_artifacts(
        response,
        program_ir=program_ir,
        config=config,
        action_id=action_id,
        input_payload=payload,
        state_snapshot=response.get("state") if isinstance(response, dict) else None,
        endpoint="/api/action",
    )
    runtime_errors = response.get("runtime_errors")
    ui_payload = response.get("ui")
    if isinstance(runtime_errors, list) and runtime_errors and isinstance(ui_payload, dict):
        inject_runtime_error_elements(ui_payload, runtime_errors)
    retrieval_result = _normalize_retrieval_result(response.get("result"))
    if isinstance(retrieval_result, dict) and isinstance(ui_payload, dict):
        inject_retrieval_explain_elements(ui_payload, retrieval_result)
    if isinstance(ui_payload, dict):
        ui_mode = str(ui_payload.get("mode") or "").strip().lower()
        if ui_mode == DISPLAY_MODE_STUDIO:
            inject_audit_viewer_elements(
                ui_payload,
                run_artifact=response.get("run_artifact"),
                audit_bundle=response.get("audit_bundle"),
                audit_policy_status=response.get("audit_policy_status"),
            )
    return response


def _normalize_retrieval_result(value: object) -> dict | None:
    if not isinstance(value, dict):
        return None
    retrieval = value.get("retrieval")
    if isinstance(retrieval, dict):
        return retrieval
    return None


__all__ = ["dispatch_ui_action"]
