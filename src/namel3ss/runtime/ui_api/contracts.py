from __future__ import annotations

from typing import Any

from namel3ss.ui.export.actions import build_actions_list
from namel3ss.ui.manifest.page_structure import page_diagnostics_elements, walk_elements, walk_page_elements

UI_API_VERSION = "1"


def build_ui_manifest_payload(manifest_payload: dict, *, revision: str | None = None) -> dict:
    if not isinstance(manifest_payload, dict):
        return _error_payload("Invalid manifest payload", revision=revision)
    if not manifest_payload.get("ok", True):
        return _error_payload(_error_message(manifest_payload), revision=revision)
    pages = manifest_payload.get("pages")
    page_items = pages if isinstance(pages, list) else []
    actions = manifest_payload.get("actions")
    action_map = actions if isinstance(actions, dict) else {}
    flows = _sorted_unique(_collect_flow_names(action_map))
    components = _sorted_unique(_collect_component_types(page_items))
    theme = manifest_payload.get("theme") if isinstance(manifest_payload.get("theme"), dict) else {}
    payload = {
        "ok": True,
        "api_version": UI_API_VERSION,
        "manifest": {
            "pages": page_items,
            "flows": flows,
            "components": components,
        },
        "theme": theme,
    }
    upload_requests = manifest_payload.get("upload_requests")
    if isinstance(upload_requests, list):
        payload["manifest"]["upload_requests"] = [entry for entry in upload_requests if isinstance(entry, dict)]
    warnings = _normalize_warnings(manifest_payload.get("warnings"))
    if warnings:
        payload["manifest"]["warnings"] = warnings
    mode = manifest_payload.get("mode")
    if isinstance(mode, str) and mode:
        payload["manifest"]["mode"] = mode
    diagnostics_enabled = manifest_payload.get("diagnostics_enabled")
    if isinstance(diagnostics_enabled, bool):
        payload["manifest"]["diagnostics_enabled"] = diagnostics_enabled
    if isinstance(revision, str) and revision:
        payload["revision"] = revision
    return payload


def build_ui_actions_payload(manifest_payload: dict, *, revision: str | None = None) -> dict:
    if not isinstance(manifest_payload, dict):
        return _error_payload("Invalid manifest payload", revision=revision)
    if not manifest_payload.get("ok", True):
        return _error_payload(_error_message(manifest_payload), revision=revision)
    actions = manifest_payload.get("actions")
    action_map = actions if isinstance(actions, dict) else {}
    payload = {
        "ok": True,
        "api_version": UI_API_VERSION,
        "actions": build_actions_list(action_map),
    }
    warnings = _normalize_warnings(manifest_payload.get("warnings"))
    if warnings:
        payload["warnings"] = warnings
    if isinstance(revision, str) and revision:
        payload["revision"] = revision
    return payload


def build_ui_state_payload(state_payload: dict, *, revision: str | None = None) -> dict:
    if not isinstance(state_payload, dict):
        return _error_payload("Invalid state payload", revision=revision)
    if not state_payload.get("ok", True):
        return _error_payload(_error_message(state_payload), revision=revision)
    state = state_payload.get("state") if isinstance(state_payload.get("state"), dict) else {}
    current_page = state.get("page") if isinstance(state.get("page"), str) else None
    errors = _normalize_errors(state_payload.get("error"))
    payload = {
        "ok": True,
        "api_version": UI_API_VERSION,
        "state": {
            "current_page": current_page,
            "values": state,
            "errors": errors,
        },
    }
    resolved_revision = state_payload.get("revision") if isinstance(state_payload.get("revision"), str) else revision
    if isinstance(resolved_revision, str) and resolved_revision:
        payload["revision"] = resolved_revision
    return payload


def build_action_result_payload(action_payload: dict, *, revision: str | None = None) -> dict:
    if not isinstance(action_payload, dict):
        return {
            "ok": False,
            "api_version": UI_API_VERSION,
            "success": False,
            "new_state": {},
            "message": "Invalid action payload",
        }
    ok = bool(action_payload.get("ok", False))
    new_state = action_payload.get("state") if isinstance(action_payload.get("state"), dict) else {}
    error = action_payload.get("error")
    message = _error_text(error)
    if ok and not message:
        message = "Action completed"
    payload = {
        "ok": ok,
        "api_version": UI_API_VERSION,
        "success": ok,
        "new_state": new_state,
        "message": message,
    }
    if ok and "result" in action_payload:
        payload["result"] = action_payload.get("result")
    resolved_revision = action_payload.get("revision") if isinstance(action_payload.get("revision"), str) else revision
    if isinstance(resolved_revision, str) and resolved_revision:
        payload["revision"] = resolved_revision
    return payload


def _collect_flow_names(action_map: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for action in action_map.values():
        if not isinstance(action, dict):
            continue
        if action.get("type") != "call_flow":
            continue
        flow_name = action.get("flow")
        if isinstance(flow_name, str) and flow_name:
            names.append(flow_name)
    return names


def _collect_component_types(pages: list[dict]) -> list[str]:
    types: list[str] = []
    for page in pages:
        if not isinstance(page, dict):
            continue
        for element in walk_page_elements(page):
            element_type = element.get("type") if isinstance(element, dict) else None
            if isinstance(element_type, str) and element_type:
                types.append(element_type)
        diagnostics_blocks = page_diagnostics_elements(page)
        for element in walk_elements(diagnostics_blocks):
            element_type = element.get("type") if isinstance(element, dict) else None
            if isinstance(element_type, str) and element_type:
                types.append(element_type)
    return types

def _sorted_unique(values: list[str]) -> list[str]:
    return sorted({value for value in values if isinstance(value, str) and value})


def _normalize_errors(error_payload: Any) -> list[dict]:
    if isinstance(error_payload, list):
        return [item for item in error_payload if isinstance(item, dict)]
    if isinstance(error_payload, dict):
        return [error_payload]
    return []


def _normalize_warnings(warnings_payload: Any) -> list[dict]:
    if isinstance(warnings_payload, list):
        return [item for item in warnings_payload if isinstance(item, dict)]
    return []


def _error_text(error_payload: Any) -> str:
    if isinstance(error_payload, dict):
        for key in ("message", "error", "why"):
            value = error_payload.get(key)
            if isinstance(value, str) and value:
                return value
    if isinstance(error_payload, str):
        return error_payload
    return ""


def _error_message(payload: dict) -> str:
    error = payload.get("error")
    text = _error_text(error)
    if text:
        return text
    return "Request failed"


def _error_payload(message: str, *, revision: str | None = None) -> dict:
    payload = {
        "ok": False,
        "api_version": UI_API_VERSION,
        "error": {"message": message},
    }
    if isinstance(revision, str) and revision:
        payload["revision"] = revision
    return payload


__all__ = [
    "UI_API_VERSION",
    "build_action_result_payload",
    "build_ui_actions_payload",
    "build_ui_manifest_payload",
    "build_ui_state_payload",
]
