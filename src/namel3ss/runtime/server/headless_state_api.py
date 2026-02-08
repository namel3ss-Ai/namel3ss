from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from namel3ss.errors.payload import build_error_payload
from namel3ss.runtime.server.headless_api import (
    authorize_headless_preflight,
    authorize_headless_request,
    build_headless_action_payload,
    build_headless_ui_payload,
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
        handler._respond_json(unsupported_version_payload(), status=404)
        return True
    gate = authorize_headless_request(
        path=path,
        headers=dict(handler.headers.items()),
        headless=bool(getattr(handler.server, "headless", False)),  # type: ignore[attr-defined]
        api_token=getattr(handler.server, "headless_api_token", None),  # type: ignore[attr-defined]
        cors_origins=getattr(handler.server, "headless_cors_origins", ()),  # type: ignore[attr-defined]
    )
    if not gate.ok:
        handler._respond_json(gate.payload or build_error_payload("Request blocked", kind="engine"), status=gate.status, headers=gate.headers)
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
        handler._respond_json(unsupported_version_payload(), status=404)
        return True
    gate = authorize_headless_request(
        path=path,
        headers=dict(handler.headers.items()),
        headless=bool(getattr(handler.server, "headless", False)),  # type: ignore[attr-defined]
        api_token=getattr(handler.server, "headless_api_token", None),  # type: ignore[attr-defined]
        cors_origins=getattr(handler.server, "headless_cors_origins", ()),  # type: ignore[attr-defined]
    )
    if not gate.ok:
        handler._respond_json(gate.payload or build_error_payload("Request blocked", kind="engine"), status=gate.status, headers=gate.headers)
        return True
    action_payload, payload_error = normalize_headless_action_payload(body)
    if payload_error is not None:
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


__all__ = [
    "handle_stateful_headless_get",
    "handle_stateful_headless_options",
    "handle_stateful_headless_post",
]
