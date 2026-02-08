from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.payload import build_error_from_exception, build_error_payload
from namel3ss.runtime.server.headless_api import (
    authorize_headless_preflight,
    authorize_headless_request,
    build_headless_action_payload,
    build_headless_ui_payload,
    headless_ui_response_headers,
    headless_action_id,
    is_headless_ui_path,
    is_versioned_api_path,
    merge_response_headers,
    normalize_headless_action_payload,
    query_flag,
    request_etag_matches,
    unsupported_version_payload,
)
from namel3ss.runtime.server.service_sessions_api import session_manager
from namel3ss.ui.actions.dispatch import dispatch_ui_action
from namel3ss.ui.export.contract import build_ui_contract_payload


def handle_service_headless_get(handler, *, path: str, query: dict[str, list[str]]) -> bool:
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
    program_ir = handler._program()
    if program_ir is None:
        handler._respond_json(build_error_payload("Program not loaded", kind="engine"), status=500, headers=gate.headers)
        return True
    if session_manager(handler) is not None and str(query.get("session_id", [""])[0]).strip():
        payload = build_error_payload("Session-aware /api/v1/ui is not supported. Use /api/ui/manifest for session requests.", kind="engine")
        handler._respond_json(payload, status=400, headers=gate.headers)
        return True
    ui_mode = getattr(handler.server, "ui_mode", "production")  # type: ignore[attr-defined]
    diagnostics_enabled = bool(getattr(handler.server, "ui_diagnostics_enabled", False))  # type: ignore[attr-defined]
    contract = build_ui_contract_payload(program_ir, ui_mode=ui_mode, diagnostics_enabled=diagnostics_enabled)
    include_state = query_flag(query, "include_state")
    include_actions = query_flag(query, "include_actions")
    state_payload = _service_state_payload(handler) if include_state else None
    actions_payload = contract.get("actions") if include_actions and isinstance(contract.get("actions"), dict) else None
    revision = getattr(handler._program_state(), "revision", "")
    payload = build_headless_ui_payload(
        manifest=contract.get("ui") if isinstance(contract.get("ui"), dict) else {},
        revision=revision if isinstance(revision, str) else None,
        state=state_payload,
        actions=actions_payload,
    )
    status = 200 if payload.get("ok", True) else 400
    response_headers = merge_response_headers(
        gate.headers,
        headless_ui_response_headers(
            payload,
            include_state=include_state,
            include_actions=include_actions,
        ),
    )
    if status == 200:
        etag = response_headers.get("ETag")
        if isinstance(etag, str) and request_etag_matches(dict(handler.headers.items()), etag):
            handler.send_response(304)
            for key, value in response_headers.items():
                handler.send_header(key, value)
            handler.end_headers()
            return True
    handler._respond_json(payload, status=status, sort_keys=True, headers=response_headers)
    return True


def handle_service_headless_post(handler, *, path: str, body: dict | None) -> bool:
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
    response, status, extra_headers = _run_service_action(handler, action_id=action_id, payload=action_payload or {})
    normalized, normalized_status = build_headless_action_payload(action_id=action_id, action_response=response)
    headers = merge_response_headers(gate.headers, extra_headers)
    handler._respond_json(normalized, status=normalized_status if status == 200 else status, headers=headers)
    return True


def handle_service_headless_options(handler, *, path: str) -> bool:
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


def _service_state_payload(handler) -> dict:
    state = handler._program_state()
    revision = getattr(state, "revision", "") if state is not None else ""
    return {
        "ok": True,
        "api_version": "1",
        "state": {"current_page": None, "values": {}, "errors": []},
        "revision": revision,
    }


def _run_service_action(handler, *, action_id: str, payload: dict) -> tuple[dict, int, dict[str, str]]:
    if session_manager(handler) is not None:
        return build_error_payload("Session-aware /api/v1/actions is not supported. Use /api/action with session_id.", kind="engine"), 400, {}
    program_ir = handler._program()
    if program_ir is None:
        return build_error_payload("Program not loaded", kind="engine"), 500, {}
    try:
        worker_pool = getattr(handler.server, "worker_pool", None)  # type: ignore[attr-defined]
        if worker_pool is not None:
            response = worker_pool.run_action(action_id, payload)
        else:
            ui_mode = getattr(handler.server, "ui_mode", "production")  # type: ignore[attr-defined]
            diagnostics_enabled = bool(getattr(handler.server, "ui_diagnostics_enabled", False))  # type: ignore[attr-defined]
            response = dispatch_ui_action(
                program_ir,
                action_id=action_id,
                payload=payload,
                ui_mode=ui_mode,
                diagnostics_enabled=diagnostics_enabled,
            )
        if isinstance(response, dict):
            if worker_pool is not None:
                response.setdefault("process_model", "worker_pool")
            return response, 200 if response.get("ok", True) else 400, {}
        return build_error_payload("Action response invalid", kind="engine"), 500, {}
    except Namel3ssError as err:
        return build_error_from_exception(err, kind="engine"), 400, {}
    except Exception as err:  # pragma: no cover - defensive
        return build_error_payload(f"Action failed: {err}", kind="engine"), 500, {}


__all__ = [
    "handle_service_headless_get",
    "handle_service_headless_options",
    "handle_service_headless_post",
]
