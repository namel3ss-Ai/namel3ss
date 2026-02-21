from __future__ import annotations

from copy import deepcopy
from urllib.parse import parse_qs, urlparse

from namel3ss.config.loader import load_config
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.payload import build_error_from_exception, build_error_payload
from namel3ss.runtime.audit.runtime_capture import attach_audit_artifacts
from namel3ss.runtime.executor import execute_program_flow
from namel3ss.runtime.server.session_manager import ServiceSession
from namel3ss.runtime.ui.actions import handle_action
from namel3ss.ui.manifest.elements.audit_viewer import inject_audit_viewer_elements
from namel3ss.ui.manifest.display_mode import DISPLAY_MODE_STUDIO
from namel3ss.ui.manifest import build_manifest
from namel3ss.ui.settings import UI_DEFAULTS



def session_manager(handler):
    return getattr(handler.server, "session_manager", None)  # type: ignore[attr-defined]



def cleanup_session_manager(handler) -> None:
    manager = session_manager(handler)
    if manager is not None:
        manager.cleanup_idle_sessions()



def handle_session_manifest_get(handler, query: dict[str, list[str]]) -> None:
    manager = session_manager(handler)
    if manager is None:
        handler._respond_json(build_error_payload(_service_capability_missing_message(), kind="engine"), status=403)
        return
    program_ir = handler._program()
    if program_ir is None:
        handler._respond_json(build_error_payload("Program not loaded", kind="engine"), status=500)
        return
    try:
        session = resolve_request_session(handler, manager=manager, query=query, payload=None, create_if_missing=True)
        manifest = build_session_manifest(handler, program_ir, session)
        handler._respond_json(
            {
                **manifest,
                "session_id": session.session_id,
                "role": session.role,
            },
            status=200,
            sort_keys=True,
            headers={"X-N3-Session-Id": session.session_id},
        )
    except Namel3ssError as err:
        handler._respond_json(build_error_from_exception(err, kind="engine"), status=400)



def handle_session_state_get(handler, query: dict[str, list[str]]) -> None:
    manager = session_manager(handler)
    if manager is None:
        handler._respond_json(build_error_payload(_service_capability_missing_message(), kind="engine"), status=403)
        return
    try:
        session = resolve_request_session(handler, manager=manager, query=query, payload=None, create_if_missing=True)
        payload = {
            "ok": True,
            "api_version": "1",
            "session_id": session.session_id,
            "role": session.role,
            "state": {
                "current_page": None,
                "values": deepcopy(session.state),
                "errors": [],
            },
            "revision": getattr(handler._program_state(), "revision", ""),
        }
        handler._respond_json(payload, status=200, sort_keys=True, headers={"X-N3-Session-Id": session.session_id})
    except Namel3ssError as err:
        handler._respond_json(build_error_from_exception(err, kind="engine"), status=400)



def handle_session_action_post(handler, body: dict, *, action_id: str, payload: dict, program_ir) -> None:
    manager = session_manager(handler)
    if manager is None:
        handler._respond_json(build_error_payload(_service_capability_missing_message(), kind="engine"), status=403)
        return
    try:
        session = resolve_request_session(
            handler,
            manager=manager,
            query=parse_qs(urlparse(handler.path).query or ""),
            payload=body,
            create_if_missing=True,
        )
        config = load_config(
            app_path=getattr(program_ir, "app_path", None),
            root=getattr(program_ir, "project_root", None),
        )
        response = handle_action(
            program_ir,
            action_id=action_id,
            payload=payload,
            state=session.state,
            store=session.store,
            runtime_theme=session.runtime_theme or getattr(program_ir, "theme", UI_DEFAULTS["theme"]),
            memory_manager=session.memory_manager,
            config=config,
            identity=identity_for_session(session),
            session={"id": session.session_id, "role": session.role},
            source=main_source(handler),
            raise_on_error=False,
            ui_mode=getattr(handler.server, "ui_mode", "production"),  # type: ignore[attr-defined]
        )
        if isinstance(response, dict):
            response = attach_audit_artifacts(
                response,
                program_ir=program_ir,
                config=config,
                action_id=action_id,
                input_payload=payload,
                state_snapshot=response.get("state") if isinstance(response.get("state"), dict) else session.state,
                source=main_source(handler),
                endpoint="/api/action",
            )
            if isinstance(response.get("state"), dict):
                session.state = deepcopy(response["state"])
            ui_payload = response.get("ui")
            if isinstance(ui_payload, dict):
                ui_mode = str(ui_payload.get("mode") or "").strip().lower()
                if ui_mode == DISPLAY_MODE_STUDIO:
                    inject_audit_viewer_elements(
                        ui_payload,
                        run_artifact=response.get("run_artifact"),
                        audit_bundle=response.get("audit_bundle"),
                        audit_policy_status=response.get("audit_policy_status"),
                    )
                theme_current = (ui_payload.get("theme") or {}).get("current")
                if isinstance(theme_current, str) and theme_current:
                    session.runtime_theme = theme_current
            manager.record_trace(
                session.session_id,
                {
                    "type": "action",
                    "action_id": action_id,
                    "ok": bool(response.get("ok", True)),
                },
            )
            response.setdefault("session_id", session.session_id)
            response.setdefault("role", session.role)
            status = 200 if response.get("ok", True) else 400
            handler._respond_json(response, status=status, headers={"X-N3-Session-Id": session.session_id})
            return
        handler._respond_json(build_error_payload("Action response invalid", kind="engine"), status=500)
    except Namel3ssError as err:
        handler._respond_json(build_error_from_exception(err, kind="engine"), status=400)
    except Exception as err:  # pragma: no cover - defensive
        handler._respond_json(build_error_payload(f"Action failed: {err}", kind="engine"), status=500)



def handle_session_create_post(handler, body: dict) -> None:
    manager = session_manager(handler)
    if manager is None:
        handler._respond_json(build_error_payload(_service_capability_missing_message(), kind="engine"), status=403)
        return
    try:
        role = body.get("role") if isinstance(body, dict) else None
        session = manager.ensure_session(session_id=None, requested_role=role if isinstance(role, str) else None, create_if_missing=True)
        manager.record_trace(session.session_id, {"type": "session_created", "role": session.role})
        payload = {
            "ok": True,
            "session_id": session.session_id,
            "role": session.role,
        }
        handler._respond_json(payload, status=200, headers={"X-N3-Session-Id": session.session_id})
    except Namel3ssError as err:
        handler._respond_json(build_error_from_exception(err, kind="engine"), status=400)



def handle_session_list_get(handler) -> None:
    manager = session_manager(handler)
    if manager is None:
        handler._respond_json(build_error_payload(_service_capability_missing_message(), kind="engine"), status=403)
        return
    payload = {"ok": True, "sessions": manager.list_sessions()}
    handler._respond_json(payload, status=200, sort_keys=True)



def handle_session_kill_delete(handler, session_id: str) -> None:
    manager = session_manager(handler)
    if manager is None:
        handler._respond_json(build_error_payload(_service_capability_missing_message(), kind="engine"), status=403)
        return
    session_id = str(session_id or "").strip()
    if not session_id:
        handler._respond_json(build_error_payload("Session id is required", kind="engine"), status=400)
        return
    killed = manager.kill_session(session_id)
    if not killed:
        handler._respond_json(build_error_payload(f"Session '{session_id}' was not found", kind="engine"), status=404)
        return
    payload = {"ok": True, "killed": True, "session_id": session_id}
    handler._respond_json(payload, status=200)



def handle_remote_studio_get(handler, normalized_path: str) -> None:
    manager = session_manager(handler)
    if manager is None:
        handler._respond_json(build_error_payload(_service_capability_missing_message(), kind="engine"), status=403)
        return
    if not manager.remote_studio_enabled:
        handler._respond_json(build_error_payload(_remote_studio_capability_missing_message(), kind="engine"), status=403)
        return
    parts = normalized_path.strip("/").split("/")
    # expected: api/service/studio/<session_id>/state|traces
    if len(parts) != 5:
        handler.send_error(404)
        return
    _, _, _, session_id, resource = parts
    try:
        if resource == "state":
            payload = {"ok": True, **manager.studio_state(session_id)}
            handler._respond_json(payload, status=200, sort_keys=True)
            return
        if resource == "traces":
            payload = {"ok": True, "session_id": session_id, "traces": manager.studio_traces(session_id)}
            handler._respond_json(payload, status=200, sort_keys=True)
            return
        handler.send_error(404)
    except Namel3ssError as err:
        handler._respond_json(build_error_from_exception(err, kind="engine"), status=404)



def resolve_request_session(
    handler,
    *,
    manager,
    query: dict[str, list[str]],
    payload: dict | None,
    create_if_missing: bool,
) -> ServiceSession:
    session_id = _session_id_from_request(handler.headers, query, payload)
    role = _role_from_request(handler.headers, payload)
    return manager.ensure_session(
        session_id=session_id,
        requested_role=role,
        create_if_missing=create_if_missing,
    )



def identity_for_session(session: ServiceSession) -> dict:
    return {
        "subject": f"session:{session.session_id}",
        "role": session.role,
        "roles": [session.role],
        "session_id": session.session_id,
    }



def build_session_manifest(handler, program_ir, session: ServiceSession) -> dict:
    config = load_config(
        app_path=getattr(program_ir, "app_path", None),
        root=getattr(program_ir, "project_root", None),
    )
    runtime_theme = session.runtime_theme or getattr(program_ir, "theme", UI_DEFAULTS["theme"])
    manifest = build_manifest(
        program_ir,
        config=config,
        state=session.state,
        store=session.store,
        runtime_theme=runtime_theme,
        identity=identity_for_session(session),
        auth_context=None,
        display_mode=getattr(handler.server, "ui_mode", "production"),  # type: ignore[attr-defined]
        diagnostics_enabled=bool(getattr(handler.server, "ui_diagnostics_enabled", False)),  # type: ignore[attr-defined]
    )
    current = (manifest.get("theme") or {}).get("current")
    if isinstance(current, str) and current:
        session.runtime_theme = current
    return manifest



def main_source(handler) -> str | None:
    program_state = handler._program_state()
    sources = getattr(program_state, "sources", None)
    app_path = getattr(program_state, "app_path", None)
    if isinstance(sources, dict) and app_path in sources:
        return sources.get(app_path)
    return None



def resolve_dynamic_route_context(handler, program, worker_pool):
    manager = session_manager(handler)
    if manager is None:
        flow_executor = worker_pool.run_flow if worker_pool is not None else None
        store = handler._ensure_store(program)
        return flow_executor, store, None, {}

    session = resolve_request_session(
        handler,
        manager=manager,
        query=parse_qs(urlparse(handler.path).query or ""),
        payload=None,
        create_if_missing=True,
    )

    def _flow_executor(*, program, flow_name, input, identity, auth_context, route_name, config, **_unused):
        result = execute_program_flow(
            program=program,
            flow_name=flow_name,
            state=session.state,
            input=input,
            store=session.store,
            identity=identity_for_session(session),
            auth_context=auth_context,
            route_name=route_name,
            config=config,
            session={"id": session.session_id, "role": session.role},
        )
        session.state = session.store.load_state()
        manager.record_trace(
            session.session_id,
            {"type": "route", "route_name": route_name or "", "flow_name": flow_name, "ok": True},
        )
        return result

    return _flow_executor, session.store, identity_for_session(session), {"X-N3-Session-Id": session.session_id}



def _query_value(query: dict[str, list[str]], name: str) -> str | None:
    values = query.get(name) or []
    if not values:
        return None
    value = str(values[0] or "").strip()
    return value or None



def _header_value(headers, key: str) -> str | None:
    for name, value in headers.items():
        if str(name).lower() == key.lower():
            normalized = str(value or "").strip()
            return normalized or None
    return None



def _session_id_from_request(headers, query: dict[str, list[str]], payload: dict | None) -> str | None:
    from_payload = None
    if isinstance(payload, dict):
        candidate = payload.get("session_id")
        if isinstance(candidate, str):
            from_payload = candidate.strip() or None
    return _header_value(headers, "X-N3-Session-Id") or _query_value(query, "session_id") or from_payload



def _role_from_request(headers, payload: dict | None) -> str | None:
    from_payload = None
    if isinstance(payload, dict):
        candidate = payload.get("role")
        if isinstance(candidate, str):
            from_payload = candidate.strip().lower() or None
    header_value = _header_value(headers, "X-N3-Role")
    if header_value:
        return header_value.strip().lower()
    return from_payload



def _service_capability_missing_message() -> str:
    return (
        'Service session APIs require capability "service". '
        "Add service to your app capabilities and restart."
    )



def _remote_studio_capability_missing_message() -> str:
    return (
        'Remote Studio APIs require capability "remote_studio". '
        "Add remote_studio to your app capabilities and restart."
    )


__all__ = [
    "build_session_manifest",
    "cleanup_session_manager",
    "handle_remote_studio_get",
    "handle_session_action_post",
    "handle_session_create_post",
    "handle_session_kill_delete",
    "handle_session_list_get",
    "handle_session_manifest_get",
    "handle_session_state_get",
    "resolve_dynamic_route_context",
    "resolve_request_session",
    "session_manager",
]
