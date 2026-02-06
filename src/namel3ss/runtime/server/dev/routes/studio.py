from __future__ import annotations

from typing import Any, Callable

from namel3ss.config.loader import load_config
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.payload import build_error_from_exception, build_error_payload
from namel3ss.runtime.auth.auth_context import resolve_auth_context
from namel3ss.runtime.auth.auth_routes import handle_login, handle_logout, handle_session
from namel3ss.runtime.data.data_routes import (
    build_data_status_payload,
    build_migrations_plan_payload,
    build_migrations_status_payload,
)
from namel3ss.runtime.deploy_routes import get_build_payload, get_deploy_payload
from namel3ss.runtime.server.dev.errors import error_from_exception, error_from_message
from namel3ss.runtime.ui_api import (
    build_action_result_payload,
    build_ui_actions_payload,
    build_ui_manifest_payload,
    build_ui_state_payload,
)


def handle_session_get(handler: Any, path: str) -> bool:
    if path not in {"/api/session", "/api/auth/session"}:
        return False
    payload, status, headers = _handle_session_get(handler)
    handler._respond_json(payload, status=status, headers=headers)
    return True


def handle_ui_get(handler: Any, path: str) -> bool:
    if path != "/api/ui":
        return False
    auth_context = _auth_context_or_error(handler, kind="manifest")
    if auth_context is None:
        return True
    payload = handler._state().manifest_payload(identity=auth_context.identity, auth_context=auth_context)
    status = 200 if payload.get("ok", True) else 400
    handler._respond_json(payload, status=status)
    return True


def handle_ui_manifest_get(handler: Any, path: str) -> bool:
    if path != "/api/ui/manifest":
        return False
    auth_context = _auth_context_or_error(handler, kind="manifest")
    if auth_context is None:
        return True
    state = handler._state()
    manifest = state.manifest_payload(identity=auth_context.identity, auth_context=auth_context)
    payload = build_ui_manifest_payload(manifest, revision=state.revision)
    status = 200 if payload.get("ok", True) else 400
    handler._respond_json(payload, status=status)
    return True


def handle_state_get(handler: Any, path: str) -> bool:
    if path != "/api/state":
        return False
    auth_context = _auth_context_or_error(handler, kind="state")
    if auth_context is None:
        return True
    payload = handler._state().state_payload(identity=auth_context.identity)
    status = 200 if payload.get("ok", True) else 400
    handler._respond_json(payload, status=status)
    return True


def handle_ui_state_get(handler: Any, path: str) -> bool:
    if path != "/api/ui/state":
        return False
    auth_context = _auth_context_or_error(handler, kind="state")
    if auth_context is None:
        return True
    state = handler._state()
    payload = state.state_payload(identity=auth_context.identity)
    ui_payload = build_ui_state_payload(payload, revision=state.revision)
    status = 200 if ui_payload.get("ok", True) else 400
    handler._respond_json(ui_payload, status=status)
    return True


def handle_ui_actions_get(handler: Any, path: str) -> bool:
    if path != "/api/ui/actions":
        return False
    auth_context = _auth_context_or_error(handler, kind="manifest")
    if auth_context is None:
        return True
    state = handler._state()
    manifest = state.manifest_payload(identity=auth_context.identity, auth_context=auth_context)
    payload = build_ui_actions_payload(manifest, revision=state.revision)
    status = 200 if payload.get("ok", True) else 400
    handler._respond_json(payload, status=status)
    return True


def handle_data_status_get(handler: Any, path: str) -> bool:
    if path != "/api/data/status":
        return False
    payload = _data_status_payload(handler)
    status = 200 if payload.get("ok", True) else 400
    handler._respond_json(payload, status=status)
    return True


def handle_migrations_status_get(handler: Any, path: str) -> bool:
    if path != "/api/migrations/status":
        return False
    payload = _migrations_status_payload(handler)
    status = 200 if payload.get("ok", True) else 400
    handler._respond_json(payload, status=status)
    return True


def handle_migrations_plan_get(handler: Any, path: str) -> bool:
    if path != "/api/migrations/plan":
        return False
    payload = _migrations_plan_payload(handler)
    status = 200 if payload.get("ok", True) else 400
    handler._respond_json(payload, status=status)
    return True


def handle_build_get(handler: Any, path: str) -> bool:
    if path != "/api/build":
        return False
    payload = _build_payload(handler)
    status = 200 if payload.get("ok", True) else 400
    handler._respond_json(payload, status=status)
    return True


def handle_deploy_get(handler: Any, path: str) -> bool:
    if path != "/api/deploy":
        return False
    payload = _deploy_payload(handler)
    status = 200 if payload.get("ok", True) else 400
    handler._respond_json(payload, status=status)
    return True


def handle_action_post(handler: Any, body: dict) -> None:
    if not isinstance(body, dict):
        handler._respond_json(build_error_payload("Body must be a JSON object.", kind="engine"), status=400)
        return
    action_id = body.get("id")
    payload = body.get("payload") or {}
    if not isinstance(action_id, str):
        handler._respond_json(build_error_payload("Action id is required.", kind="engine"), status=400)
        return
    if not isinstance(payload, dict):
        handler._respond_json(build_error_payload("Payload must be an object.", kind="engine"), status=400)
        return
    auth_context = _auth_context_or_error(handler, kind="engine")
    if auth_context is None:
        return
    response = handler._state().run_action(
        action_id,
        payload,
        identity=auth_context.identity,
        auth_context=auth_context,
    )
    status = 200 if response.get("ok", True) else 400
    handler._respond_json(response, status=status)


def handle_ui_action_post(handler: Any, body: dict) -> None:
    if not isinstance(body, dict):
        handler._respond_json(build_error_payload("Body must be a JSON object.", kind="engine"), status=400)
        return
    action_id = body.get("id")
    payload = body.get("payload") or {}
    if not isinstance(action_id, str):
        handler._respond_json(build_error_payload("Action id is required.", kind="engine"), status=400)
        return
    if not isinstance(payload, dict):
        handler._respond_json(build_error_payload("Payload must be an object.", kind="engine"), status=400)
        return
    auth_context = _auth_context_or_error(handler, kind="engine")
    if auth_context is None:
        return
    state = handler._state()
    response = state.run_action(
        action_id,
        payload,
        identity=auth_context.identity,
        auth_context=auth_context,
    )
    ui_response = build_action_result_payload(response, revision=state.revision)
    status = 200 if ui_response.get("ok", False) else 400
    handler._respond_json(ui_response, status=status)


def handle_login_post(handler: Any, body: dict) -> tuple[dict, int, dict[str, str]]:
    try:
        config, identity_schema, store = _auth_params(handler)
    except Namel3ssError as err:
        return build_error_from_exception(err, kind="authentication"), 400, {}
    return handle_login(
        dict(handler.headers.items()),
        body,
        config=config,
        identity_schema=identity_schema,
        store=store,
    )


def handle_logout_post(handler: Any) -> tuple[dict, int, dict[str, str]]:
    try:
        config, identity_schema, store = _auth_params(handler)
    except Namel3ssError as err:
        return build_error_from_exception(err, kind="authentication"), 400, {}
    state = handler._state()
    return handle_logout(
        dict(handler.headers.items()),
        config=config,
        identity_schema=identity_schema,
        store=store,
        project_root=str(getattr(state, "project_root", "") or "") or None,
        app_path=str(getattr(state, "app_path", "") or "") or None,
    )


def _handle_session_get(handler: Any) -> tuple[dict, int, dict[str, str]]:
    try:
        config, identity_schema, store = _auth_params(handler)
    except Namel3ssError as err:
        return build_error_from_exception(err, kind="authentication"), 400, {}
    state = handler._state()
    return handle_session(
        dict(handler.headers.items()),
        config=config,
        identity_schema=identity_schema,
        store=store,
        project_root=str(getattr(state, "project_root", "") or "") or None,
        app_path=str(getattr(state, "app_path", "") or "") or None,
    )


def _auth_params(handler: Any) -> tuple[object, object | None, object]:
    state = handler._state()
    state._refresh_if_needed()
    program = state.program
    config = load_config(app_path=state.app_path)
    store = state.session.ensure_store(config)
    identity_schema = getattr(program, "identity", None) if program is not None else None
    return config, identity_schema, store


def _resolve_auth_context(handler: Any) -> object:
    config, identity_schema, store = _auth_params(handler)
    state = handler._state()
    return resolve_auth_context(
        dict(handler.headers.items()),
        config=config,
        identity_schema=identity_schema,
        store=store,
        project_root=str(getattr(state, "project_root", "") or "") or None,
        app_path=str(getattr(state, "app_path", "") or "") or None,
    )


def _auth_context_or_error(handler: Any, *, kind: str) -> object | None:
    try:
        return _resolve_auth_context(handler)
    except Namel3ssError as err:
        payload = error_from_exception(
            err,
            kind=kind,
            source=handler._state()._source_payload(),
            mode=handler._mode(),
            debug=handler._state().debug,
        )
        handler._respond_json(payload, status=400)
        return None


def _data_status_payload(handler: Any) -> dict:
    state = handler._state()
    state._refresh_if_needed()
    try:
        config = load_config(app_path=state.app_path)
        return build_data_status_payload(
            config,
            project_root=state.project_root,
            app_path=state.app_path,
        )
    except Namel3ssError as err:
        return error_from_exception(
            err,
            kind="data",
            source=state._source_payload(),
            mode=handler._mode(),
            debug=state.debug,
        )
    except Exception as err:  # pragma: no cover - defensive guard rail
        return error_from_message(
            str(err),
            kind="internal",
            mode=handler._mode(),
            debug=state.debug,
        )


def _migrations_status_payload(handler: Any) -> dict:
    return _migrations_payload(handler, build_migrations_status_payload)


def _migrations_plan_payload(handler: Any) -> dict:
    return _migrations_payload(handler, build_migrations_plan_payload)


def _migrations_payload(handler: Any, builder: Callable[..., dict]) -> dict:
    state = handler._state()
    state._refresh_if_needed()
    program = state.program
    if program is None:
        return build_error_payload("Program not loaded.", kind="engine")
    try:
        return builder(program, project_root=state.project_root)
    except Namel3ssError as err:
        return error_from_exception(
            err,
            kind="data",
            source=state._source_payload(),
            mode=handler._mode(),
            debug=state.debug,
        )
    except Exception as err:  # pragma: no cover - defensive guard rail
        return error_from_message(
            str(err),
            kind="internal",
            mode=handler._mode(),
            debug=state.debug,
        )


def _build_payload(handler: Any) -> dict:
    state = handler._state()
    state._refresh_if_needed()
    program = state.program
    root = getattr(program, "project_root", None) if program is not None else state.project_root
    app_path = getattr(program, "app_path", None) if program is not None else state.app_path
    return get_build_payload(root, app_path)


def _deploy_payload(handler: Any) -> dict:
    state = handler._state()
    state._refresh_if_needed()
    program = state.program
    root = getattr(program, "project_root", None) if program is not None else state.project_root
    app_path = getattr(program, "app_path", None) if program is not None else state.app_path
    return get_deploy_payload(root, app_path, program=program)


__all__ = [
    "handle_action_post",
    "handle_build_get",
    "handle_data_status_get",
    "handle_deploy_get",
    "handle_login_post",
    "handle_logout_post",
    "handle_migrations_plan_get",
    "handle_migrations_status_get",
    "handle_session_get",
    "handle_ui_action_post",
    "handle_ui_actions_get",
    "handle_state_get",
    "handle_ui_manifest_get",
    "handle_ui_state_get",
    "handle_ui_get",
]
