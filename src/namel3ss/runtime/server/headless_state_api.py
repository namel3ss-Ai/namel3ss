from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from namel3ss.errors.payload import build_error_payload
from namel3ss.runtime.contracts import validate_contract_payload_for_mode, with_contract_warnings
from namel3ss.runtime.server.headless_api import (
    authorize_headless_preflight,
    authorize_headless_request,
    build_headless_action_payload,
    build_headless_ui_payload,
    ensure_headless_contract_fields,
    headless_ui_response_headers,
    headless_action_id,
    is_headless_ui_path,
    is_versioned_api_path,
    normalize_headless_action_payload,
    query_flag,
    request_etag_matches,
    unsupported_version_payload,
)
from namel3ss.runtime.ui_api import build_ui_actions_payload


def handle_stateful_headless_get(handler, *, path: str, body_path: str | None = None) -> bool:
    if not is_versioned_api_path(path):
        return False
    if not is_headless_ui_path(path):
        payload = _validated_headless_payload(handler, unsupported_version_payload(), schema_name="headless_ui_response")
        handler._respond_json(payload, status=404)
        return True
    gate = authorize_headless_request(
        path=path,
        headers=dict(handler.headers.items()),
        headless=bool(getattr(handler.server, "headless", False)),  # type: ignore[attr-defined]
        api_token=getattr(handler.server, "headless_api_token", None),  # type: ignore[attr-defined]
        cors_origins=getattr(handler.server, "headless_cors_origins", ()),  # type: ignore[attr-defined]
    )
    if not gate.ok:
        blocked_payload = gate.payload or build_error_payload("Request blocked", kind="engine")
        blocked_payload = ensure_headless_contract_fields(blocked_payload)
        blocked_payload = _validated_headless_payload(handler, blocked_payload, schema_name="headless_ui_response")
        handler._respond_json(blocked_payload, status=gate.status, headers=gate.headers)
        return True
    query_map = _query_map(body_path or path)
    auth_context = handler._auth_context_or_error(kind="manifest")
    if auth_context is None:
        return True
    state = handler._state()
    manifest = state.manifest_payload(identity=getattr(auth_context, "identity", None), auth_context=auth_context)
    include_state = query_flag(query_map, "include_state")
    include_actions = query_flag(query_map, "include_actions")
    state_payload = None
    if include_state:
        state_payload = state.state_payload(identity=getattr(auth_context, "identity", None))
    actions_payload = None
    if include_actions:
        actions_payload = build_ui_actions_payload(manifest, revision=getattr(state, "revision", None))
    payload = build_headless_ui_payload(
        manifest=manifest,
        revision=getattr(state, "revision", None),
        state=state_payload,
        actions=actions_payload,
    )
    payload = _validated_headless_payload(handler, payload, schema_name="headless_ui_response")
    status = 200 if payload.get("ok", True) else 400
    response_headers = dict(gate.headers or {})
    response_headers.update(
        headless_ui_response_headers(
            payload,
            include_state=include_state,
            include_actions=include_actions,
        )
    )
    if status == 200:
        etag = response_headers.get("ETag")
        if isinstance(etag, str) and request_etag_matches(dict(handler.headers.items()), etag):
            handler.send_response(304)
            for key, value in response_headers.items():
                handler.send_header(key, value)
            handler.end_headers()
            return True
    handler._respond_json(payload, status=status, headers=response_headers)
    return True


def handle_stateful_headless_post(handler, *, path: str, body: dict | None) -> bool:
    if not is_versioned_api_path(path):
        return False
    action_id = headless_action_id(path)
    if action_id is None:
        payload = _validated_headless_payload(handler, unsupported_version_payload(), schema_name="headless_action_response")
        handler._respond_json(payload, status=404)
        return True
    gate = authorize_headless_request(
        path=path,
        headers=dict(handler.headers.items()),
        headless=bool(getattr(handler.server, "headless", False)),  # type: ignore[attr-defined]
        api_token=getattr(handler.server, "headless_api_token", None),  # type: ignore[attr-defined]
        cors_origins=getattr(handler.server, "headless_cors_origins", ()),  # type: ignore[attr-defined]
    )
    if not gate.ok:
        blocked_payload = gate.payload or build_error_payload("Request blocked", kind="engine")
        blocked_payload = ensure_headless_contract_fields(blocked_payload)
        if isinstance(blocked_payload, dict):
            blocked_payload.setdefault("action_id", action_id)
        blocked_payload = _validated_headless_payload(handler, blocked_payload, schema_name="headless_action_response")
        handler._respond_json(blocked_payload, status=gate.status, headers=gate.headers)
        return True
    action_payload, payload_error = normalize_headless_action_payload(body)
    if payload_error is not None:
        payload_error.setdefault("action_id", action_id)
        payload_error = _validated_headless_payload(handler, payload_error, schema_name="headless_action_response")
        handler._respond_json(payload_error, status=400, headers=gate.headers)
        return True
    auth_context = handler._auth_context_or_error(kind="engine")
    if auth_context is None:
        return True
    response = handler._state().run_action(
        action_id,
        action_payload or {},
        identity=getattr(auth_context, "identity", None),
        auth_context=auth_context,
    )
    payload, status = build_headless_action_payload(action_id=action_id, action_response=response)
    payload = _validated_headless_payload(handler, payload, schema_name="headless_action_response")
    handler._respond_json(payload, status=status, headers=gate.headers)
    return True


def handle_stateful_headless_options(handler, *, path: str) -> bool:
    if not is_versioned_api_path(path):
        return False
    gate = authorize_headless_preflight(
        path=path,
        headers=dict(handler.headers.items()),
        headless=bool(getattr(handler.server, "headless", False)),  # type: ignore[attr-defined]
        cors_origins=getattr(handler.server, "headless_cors_origins", ()),  # type: ignore[attr-defined]
    )
    if not gate.ok:
        handler._respond_json(gate.payload or build_error_payload("Request blocked", kind="engine"), status=gate.status, headers=gate.headers)
        return True
    handler.send_response(gate.status)
    for key, value in (gate.headers or {}).items():
        handler.send_header(key, value)
    handler.end_headers()
    return True


def _query_map(path: str) -> dict[str, list[str]]:
    parsed = urlparse(path or "")
    return parse_qs(parsed.query or "")


def _validated_headless_payload(handler, payload: dict, *, schema_name: str) -> dict:
    warnings = validate_contract_payload_for_mode(
        payload,
        schema_name=schema_name,
        ui_mode=getattr(handler.server, "ui_mode", "production"),  # type: ignore[attr-defined]
        diagnostics_enabled=bool(getattr(handler.server, "ui_diagnostics_enabled", False)),  # type: ignore[attr-defined]
    )
    annotated = with_contract_warnings(payload, warnings)
    return annotated if isinstance(annotated, dict) else payload


__all__ = [
    "handle_stateful_headless_get",
    "handle_stateful_headless_options",
    "handle_stateful_headless_post",
]
