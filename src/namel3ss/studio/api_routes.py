from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from namel3ss.config.loader import load_config
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.payload import build_error_from_exception, build_error_payload
from namel3ss.module_loader import load_project
from namel3ss.studio.api import (
    get_actions_payload,
    apply_agent_wizard_wrapper,
    get_agents_payload_wrapper,
    get_diagnostics_payload,
    get_lint_payload,
    run_agent_payload_wrapper,
    run_handoff_payload_wrapper,
    update_memory_packs_wrapper,
    get_secrets_payload,
    get_summary_payload,
    get_tools_payload,
    get_ui_payload,
)
from namel3ss.studio.graph_api import get_exports_payload, get_graph_payload
from namel3ss.studio.formulas_api import get_formulas_payload
from namel3ss.studio.state_api import get_state_payload
from namel3ss.studio.routes.core import handle_action
from namel3ss.studio.why_api import get_why_payload
from namel3ss.studio.registry_api import get_registry_payload
from namel3ss.studio.deploy_api import get_build_payload_from_source, get_deploy_payload_from_source
from namel3ss.runtime.observability_api import (
    get_logs_payload,
    get_metrics_payload,
    get_trace_payload,
    get_traces_payload,
)
from namel3ss.runtime.auth.auth_routes import handle_login, handle_logout, handle_session
from namel3ss.runtime.data.studio_adapters import (
    get_data_status_payload,
    get_migrations_plan_payload,
    get_migrations_status_payload,
)


def handle_api_get(handler: Any) -> None:
    try:
        source = handler._read_source()
    except Exception as err:  # pragma: no cover - IO error edge
        payload = build_error_payload(f"Cannot read source: {err}", kind="engine")
        handler._respond_json(payload, status=500)
        return
    if handler.path == "/api/session":
        payload, status, headers = _handle_session(handler, source)
        handler._respond_json(payload, status=status, headers=headers)
        return
    if handler.path == "/api/summary":
        _respond_with_source(handler, source, get_summary_payload, kind="parse", include_app_path=True)
        return
    if handler.path == "/api/ui":
        _respond_with_source(handler, source, get_ui_payload, kind="manifest", include_session=True)
        return
    if handler.path == "/api/state":
        _respond_with_source(handler, source, get_state_payload, kind="state", include_session=True, include_app_path=True)
        return
    if handler.path == "/api/data/status":
        _respond_with_source(handler, source, get_data_status_payload, kind="data", include_app_path=True)
        return
    if handler.path == "/api/migrations/status":
        _respond_with_source(handler, source, get_migrations_status_payload, kind="data", include_app_path=True)
        return
    if handler.path == "/api/migrations/plan":
        _respond_with_source(handler, source, get_migrations_plan_payload, kind="data", include_app_path=True)
        return
    if handler.path == "/api/logs":
        payload = get_logs_payload(handler.server.project_root, handler.server.app_path)  # type: ignore[attr-defined]
        handler._respond_json(payload, status=200)
        return
    if handler.path == "/api/traces":
        payload = get_traces_payload(handler.server.project_root, handler.server.app_path)  # type: ignore[attr-defined]
        handler._respond_json(payload, status=200)
        return
    if handler.path == "/api/trace":
        payload = get_trace_payload(handler.server.project_root, handler.server.app_path)  # type: ignore[attr-defined]
        handler._respond_json(payload, status=200)
        return
    if handler.path == "/api/metrics":
        payload = get_metrics_payload(handler.server.project_root, handler.server.app_path)  # type: ignore[attr-defined]
        handler._respond_json(payload, status=200)
        return
    if handler.path == "/api/build":
        _respond_with_source(handler, source, get_build_payload_from_source, kind="build", include_app_path=True)
        return
    if handler.path == "/api/deploy":
        _respond_with_source(handler, source, get_deploy_payload_from_source, kind="deploy", include_app_path=True)
        return
    if handler.path == "/api/actions":
        _respond_with_source(handler, source, get_actions_payload, kind="manifest", include_app_path=True)
        return
    if handler.path == "/api/lint":
        payload = get_lint_payload(source)
        handler._respond_json(payload, status=200)
        return
    if handler.path == "/api/tools":
        _respond_with_source(handler, source, get_tools_payload, kind="tools", include_app_path=True)
        return
    if handler.path == "/api/secrets":
        _respond_with_source(handler, source, get_secrets_payload, kind="secrets", include_app_path=True)
        return
    if handler.path == "/api/diagnostics":
        _respond_with_source(handler, source, get_diagnostics_payload, kind="diagnostics", include_app_path=True)
        return
    if handler.path == "/api/graph":
        _respond_simple(handler, source, get_graph_payload, kind="graph")
        return
    if handler.path == "/api/exports":
        _respond_simple(handler, source, get_exports_payload, kind="exports")
        return
    if handler.path == "/api/formulas":
        payload = get_formulas_payload(source)
        status = 200 if payload.get("ok", True) else 400
        handler._respond_json(payload, status=status)
        return
    if handler.path == "/api/why":
        _respond_simple(handler, source, get_why_payload, kind="why")
        return
    if handler.path == "/api/version":
        from namel3ss.studio.api import get_version_payload

        payload = get_version_payload()
        handler._respond_json(payload, status=200)
        return
    if handler.path == "/api/agents":
        _respond_with_source(
            handler,
            source,
            get_agents_payload_wrapper,
            kind="agents",
            include_session=True,
            include_app_path=True,
        )
        return
    handler.send_error(404)


def handle_api_post(handler: Any) -> None:
    length = int(handler.headers.get("Content-Length", "0"))
    raw_body = handler.rfile.read(length) if length else b""
    try:
        body = json.loads(raw_body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        handler._respond_json(build_error_payload("Invalid JSON body", kind="parse"), status=400)
        return
    try:
        source = handler._read_source()
    except Exception as err:  # pragma: no cover
        payload = build_error_payload(f"Cannot read source: {err}", kind="engine")
        handler._respond_json(payload, status=500)
        return
    if handler.path == "/api/login":
        payload, status, headers = _handle_login(handler, source, body)
        handler._respond_json(payload, status=status, headers=headers)
        return
    if handler.path == "/api/logout":
        payload, status, headers = _handle_logout(handler, source)
        handler._respond_json(payload, status=status, headers=headers)
        return
    if handler.path == "/api/action":
        handle_action(handler, source, body)
        return
    if handler.path == "/api/agent/run":
        _respond_post(handler, source, body, run_agent_payload_wrapper, kind="agent", include_session=True, include_app_path=True)
        return
    if handler.path == "/api/agent/wizard":
        _respond_post(handler, source, body, apply_agent_wizard_wrapper, kind="agent", include_app_path=True)
        return
    if handler.path == "/api/agent/handoff":
        _respond_post(handler, source, body, run_handoff_payload_wrapper, kind="agent", include_session=True, include_app_path=True)
        return
    if handler.path == "/api/agent/memory_packs":
        _respond_post(handler, source, body, update_memory_packs_wrapper, kind="agent", include_session=True, include_app_path=True)
        return
    if handler.path == "/api/registry":
        _respond_post(handler, source, body, get_registry_payload, kind="registry", include_app_path=True)
        return
    handler.send_error(404)


def _auth_inputs(handler: Any, source: str) -> tuple[object, object | None, object]:
    app_path = Path(handler.server.app_path)  # type: ignore[attr-defined]
    project = load_project(app_path, source_overrides={app_path: source})
    config = load_config(app_path=app_path)
    store = handler._get_session().ensure_store(config)
    identity_schema = getattr(project.program, "identity", None)
    return config, identity_schema, store


def _handle_session(handler: Any, source: str) -> tuple[dict, int, dict[str, str]]:
    try:
        config, identity_schema, store = _auth_inputs(handler, source)
    except Namel3ssError as err:
        return build_error_from_exception(err, kind="authentication"), 400, {}
    return handle_session(
        dict(handler.headers.items()),
        config=config,
        identity_schema=identity_schema,
        store=store,
    )


def _handle_login(handler: Any, source: str, body: dict) -> tuple[dict, int, dict[str, str]]:
    try:
        config, identity_schema, store = _auth_inputs(handler, source)
    except Namel3ssError as err:
        return build_error_from_exception(err, kind="authentication"), 400, {}
    return handle_login(
        dict(handler.headers.items()),
        body,
        config=config,
        identity_schema=identity_schema,
        store=store,
    )


def _handle_logout(handler: Any, source: str) -> tuple[dict, int, dict[str, str]]:
    try:
        config, identity_schema, store = _auth_inputs(handler, source)
    except Namel3ssError as err:
        return build_error_from_exception(err, kind="authentication"), 400, {}
    return handle_logout(
        dict(handler.headers.items()),
        config=config,
        identity_schema=identity_schema,
        store=store,
    )


def _respond_with_source(
    handler: Any,
    source: str,
    fn,
    *,
    kind: str,
    include_session: bool = False,
    include_app_path: bool = False,
) -> None:
    try:
        if include_session:
            payload = fn(source, handler._get_session(), handler.server.app_path)  # type: ignore[attr-defined]
        elif include_app_path:
            payload = fn(source, handler.server.app_path)  # type: ignore[attr-defined]
        else:
            payload = fn(source)
        status = 200 if payload.get("ok", True) else 400
        handler._respond_json(payload, status=status)
        return
    except Namel3ssError as err:
        payload = build_error_from_exception(err, kind=kind, source=source)
        handler._respond_json(payload, status=400)
        return
    except Exception as err:  # pragma: no cover - defensive guard rail
        payload = build_error_payload(str(err), kind="internal")
        handler._respond_json(payload, status=500)
        return


def _respond_simple(handler: Any, source: str, fn, *, kind: str, allow_error: bool = False) -> None:
    try:
        payload = fn(handler.server.app_path)  # type: ignore[attr-defined]
        status = 200 if payload.get("ok", True) else 400
        handler._respond_json(payload, status=status)
        return
    except Namel3ssError as err:
        payload = build_error_from_exception(err, kind=kind, source=source)
        handler._respond_json(payload, status=400)
        return
    except Exception as err:  # pragma: no cover - defensive guard rail
        payload = build_error_payload(str(err), kind="internal")
        handler._respond_json(payload, status=500)
        return


def _respond_post(
    handler: Any,
    source: str,
    body: dict,
    fn,
    *,
    kind: str,
    include_session: bool = False,
    include_app_path: bool = False,
) -> None:
    try:
        if include_session and include_app_path:
            payload = fn(source, handler._get_session(), body, handler.server.app_path)  # type: ignore[attr-defined]
        elif include_session:
            payload = fn(source, handler._get_session(), body)
        elif include_app_path:
            payload = fn(source, body, handler.server.app_path)  # type: ignore[attr-defined]
        else:
            payload = fn(source, body)
        status = 200 if payload.get("ok", True) else 400
        handler._respond_json(payload, status=status)
        return
    except Namel3ssError as err:
        payload = build_error_from_exception(err, kind=kind, source=source)
        handler._respond_json(payload, status=400)
        return
    except Exception as err:  # pragma: no cover - defensive guard rail
        payload = build_error_payload(str(err), kind="internal")
        handler._respond_json(payload, status=500)
        return


__all__ = ["handle_api_get", "handle_api_post"]
