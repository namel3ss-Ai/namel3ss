from __future__ import annotations

from typing import Any

from namel3ss.runtime.contracts.runtime_schema import RUNTIME_UI_CONTRACT_VERSION
from namel3ss.runtime.spec_version import apply_runtime_spec_versions
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
        "contract_version": RUNTIME_UI_CONTRACT_VERSION,
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
    capabilities_enabled = _normalize_capability_packs(manifest_payload.get("capabilities_enabled"))
    if capabilities_enabled:
        payload["capabilities_enabled"] = capabilities_enabled
    capability_versions = _normalize_capability_versions(manifest_payload.get("capability_versions"))
    if capability_versions:
        payload["capability_versions"] = capability_versions
    if isinstance(revision, str) and revision:
        payload["revision"] = revision
    run_artifact = manifest_payload.get("run_artifact")
    if isinstance(run_artifact, dict):
        payload["run_artifact"] = run_artifact
    persistence_backend = manifest_payload.get("persistence_backend")
    if isinstance(persistence_backend, dict):
        payload["persistence_backend"] = persistence_backend
    state_schema_version = manifest_payload.get("state_schema_version")
    if isinstance(state_schema_version, str) and state_schema_version:
        payload["state_schema_version"] = state_schema_version
    migration_status = manifest_payload.get("migration_status")
    if isinstance(migration_status, dict):
        payload["migration_status"] = migration_status
    audit_bundle = manifest_payload.get("audit_bundle")
    if isinstance(audit_bundle, dict):
        payload["audit_bundle"] = audit_bundle
    audit_policy_status = manifest_payload.get("audit_policy_status")
    if isinstance(audit_policy_status, dict):
        payload["audit_policy_status"] = audit_policy_status
    workspace_id = _text_value(manifest_payload.get("workspace_id"))
    if workspace_id:
        payload["workspace_id"] = workspace_id
    session_id = _text_value(manifest_payload.get("session_id"))
    if session_id:
        payload["session_id"] = session_id
    run_diff = _normalize_run_diff(manifest_payload.get("run_diff"))
    if run_diff:
        payload["run_diff"] = run_diff
    repro_bundle = _normalize_json_object(manifest_payload.get("repro_bundle"))
    if repro_bundle:
        payload["repro_bundle"] = repro_bundle
    run_history = _sorted_text_list(manifest_payload.get("run_history"))
    if run_history:
        payload["run_history"] = run_history
    return apply_runtime_spec_versions(payload)


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
        "contract_version": RUNTIME_UI_CONTRACT_VERSION,
        "actions": build_actions_list(action_map),
    }
    warnings = _normalize_warnings(manifest_payload.get("warnings"))
    if warnings:
        payload["warnings"] = warnings
    if isinstance(revision, str) and revision:
        payload["revision"] = revision
    return apply_runtime_spec_versions(payload)


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
        "contract_version": RUNTIME_UI_CONTRACT_VERSION,
        "state": {
            "current_page": current_page,
            "values": state,
            "errors": errors,
        },
    }
    resolved_revision = state_payload.get("revision") if isinstance(state_payload.get("revision"), str) else revision
    if isinstance(resolved_revision, str) and resolved_revision:
        payload["revision"] = resolved_revision
    workspace_id = _text_value(state_payload.get("workspace_id"))
    if workspace_id:
        payload["workspace_id"] = workspace_id
    session_id = _text_value(state_payload.get("session_id"))
    if session_id:
        payload["session_id"] = session_id
    return apply_runtime_spec_versions(payload)


def build_action_result_payload(action_payload: dict, *, revision: str | None = None) -> dict:
    if not isinstance(action_payload, dict):
        return apply_runtime_spec_versions(
            {
            "ok": False,
            "api_version": UI_API_VERSION,
            "contract_version": RUNTIME_UI_CONTRACT_VERSION,
            "success": False,
            "new_state": {},
            "message": "Invalid action payload",
            }
        )
    ok = bool(action_payload.get("ok", False))
    new_state = action_payload.get("state") if isinstance(action_payload.get("state"), dict) else {}
    error = action_payload.get("error")
    message = _error_text(error)
    runtime_error = _normalize_runtime_error(action_payload.get("runtime_error"))
    runtime_errors = _normalize_runtime_errors(action_payload.get("runtime_errors"))
    if runtime_error and not message:
        message = runtime_error.get("message", "")
    if ok and not message:
        message = "Action completed"
    payload = {
        "ok": ok,
        "api_version": UI_API_VERSION,
        "contract_version": RUNTIME_UI_CONTRACT_VERSION,
        "success": ok,
        "new_state": new_state,
        "message": message,
    }
    if runtime_error:
        payload["runtime_error"] = runtime_error
    if runtime_errors:
        payload["runtime_errors"] = runtime_errors
    capabilities_enabled = _normalize_capability_packs(action_payload.get("capabilities_enabled"))
    if capabilities_enabled:
        payload["capabilities_enabled"] = capabilities_enabled
    capability_versions = _normalize_capability_versions(action_payload.get("capability_versions"))
    if capability_versions:
        payload["capability_versions"] = capability_versions
    persistence_backend = action_payload.get("persistence_backend")
    if isinstance(persistence_backend, dict):
        payload["persistence_backend"] = persistence_backend
    state_schema_version = action_payload.get("state_schema_version")
    if isinstance(state_schema_version, str) and state_schema_version:
        payload["state_schema_version"] = state_schema_version
    migration_status = action_payload.get("migration_status")
    if isinstance(migration_status, dict):
        payload["migration_status"] = migration_status
    run_artifact = action_payload.get("run_artifact")
    if isinstance(run_artifact, dict):
        payload["run_artifact"] = run_artifact
    audit_bundle = action_payload.get("audit_bundle")
    if isinstance(audit_bundle, dict):
        payload["audit_bundle"] = audit_bundle
    audit_policy_status = action_payload.get("audit_policy_status")
    if isinstance(audit_policy_status, dict):
        payload["audit_policy_status"] = audit_policy_status
    workspace_id = _text_value(action_payload.get("workspace_id"))
    if workspace_id:
        payload["workspace_id"] = workspace_id
    session_id = _text_value(action_payload.get("session_id"))
    if session_id:
        payload["session_id"] = session_id
    run_diff = _normalize_run_diff(action_payload.get("run_diff"))
    if run_diff:
        payload["run_diff"] = run_diff
    repro_bundle = _normalize_json_object(action_payload.get("repro_bundle"))
    if repro_bundle:
        payload["repro_bundle"] = repro_bundle
    run_history = _sorted_text_list(action_payload.get("run_history"))
    if run_history:
        payload["run_history"] = run_history
    if ok and "result" in action_payload:
        payload["result"] = action_payload.get("result")
    resolved_revision = action_payload.get("revision") if isinstance(action_payload.get("revision"), str) else revision
    if isinstance(resolved_revision, str) and resolved_revision:
        payload["revision"] = resolved_revision
    return apply_runtime_spec_versions(payload)


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


def _normalize_runtime_error(runtime_payload: Any) -> dict | None:
    if not isinstance(runtime_payload, dict):
        return None
    category = runtime_payload.get("category")
    message = runtime_payload.get("message")
    hint = runtime_payload.get("hint")
    origin = runtime_payload.get("origin")
    stable_code = runtime_payload.get("stable_code")
    if not all(isinstance(value, str) and value for value in (category, message, hint, origin, stable_code)):
        return None
    return {
        "category": category,
        "message": message,
        "hint": hint,
        "origin": origin,
        "stable_code": stable_code,
    }


def _normalize_runtime_errors(runtime_payload: Any) -> list[dict]:
    if not isinstance(runtime_payload, list):
        return []
    normalized: list[dict] = []
    seen: set[str] = set()
    for entry in runtime_payload:
        normalized_entry = _normalize_runtime_error(entry)
        if normalized_entry is None:
            continue
        stable_code = normalized_entry["stable_code"]
        if stable_code in seen:
            continue
        seen.add(stable_code)
        normalized.append(normalized_entry)
    return normalized


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
        "contract_version": RUNTIME_UI_CONTRACT_VERSION,
        "error": {"message": message},
    }
    if isinstance(revision, str) and revision:
        payload["revision"] = revision
    return apply_runtime_spec_versions(payload)


def _normalize_capability_packs(value: Any) -> list[dict]:
    if not isinstance(value, list):
        return []
    packs: list[dict] = []
    seen: set[str] = set()
    for entry in value:
        if not isinstance(entry, dict):
            continue
        name = _text_value(entry.get("name"))
        version = _text_value(entry.get("version"))
        if not name or not version:
            continue
        stable = f"{name}:{version}"
        if stable in seen:
            continue
        seen.add(stable)
        pack = {
            "name": name,
            "version": version,
            "provided_actions": _sorted_text_list(entry.get("provided_actions")),
            "required_permissions": _sorted_text_list(entry.get("required_permissions")),
            "runtime_bindings": _normalize_simple_dict(entry.get("runtime_bindings")),
            "effect_capabilities": _sorted_text_list(entry.get("effect_capabilities")),
            "contract_version": _text_value(entry.get("contract_version")),
            "purity": _text_value(entry.get("purity")),
            "replay_mode": _text_value(entry.get("replay_mode")),
        }
        packs.append(pack)
    packs.sort(key=lambda item: (item["name"], item["version"]))
    return packs


def _normalize_capability_versions(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    versions: dict[str, str] = {}
    for key in sorted(value.keys(), key=str):
        name = _text_value(key)
        version = _text_value(value.get(key))
        if not name or not version:
            continue
        versions[name] = version
    return versions


def _normalize_simple_dict(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    out: dict[str, str] = {}
    for key in sorted(value.keys(), key=str):
        key_text = _text_value(key)
        value_text = _text_value(value.get(key))
        if key_text and value_text:
            out[key_text] = value_text
    return out


def _normalize_run_diff(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    allowed = {"schema_version", "left_run_id", "right_run_id", "changed", "change_count", "changes"}
    normalized: dict[str, Any] = {}
    for key in sorted(value.keys(), key=str):
        key_text = _text_value(key)
        if key_text not in allowed:
            continue
        normalized[key_text] = value[key]
    return normalized


def _normalize_json_object(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    normalized: dict[str, Any] = {}
    for key in sorted(value.keys(), key=str):
        key_text = _text_value(key)
        if not key_text:
            continue
        normalized[key_text] = _normalize_json_value(value[key])
    return normalized


def _normalize_json_value(value: Any) -> Any:
    if isinstance(value, dict):
        return _normalize_json_object(value)
    if isinstance(value, list):
        return [_normalize_json_value(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return _text_value(value)


def _sorted_text_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    items = {_text_value(item) for item in value}
    return sorted(item for item in items if item)


def _text_value(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    return ""


__all__ = [
    "UI_API_VERSION",
    "build_action_result_payload",
    "build_ui_actions_payload",
    "build_ui_manifest_payload",
    "build_ui_state_payload",
]
