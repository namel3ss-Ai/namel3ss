from __future__ import annotations

import json
from typing import Any
from urllib.parse import parse_qs, urlparse

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.payload import build_error_from_exception, build_error_payload
from namel3ss.studio.api import (
    get_actions_payload,
    get_lint_payload,
    get_packs_payload,
    get_summary_payload,
    get_tools_payload,
    get_ui_payload,
)
from namel3ss.studio.data_api import get_audit_payload, get_data_summary_payload
from namel3ss.studio.graph_api import get_exports_payload, get_graph_payload
from namel3ss.studio.pkg_api import get_pkg_info_payload, search_pkg_index_payload
from namel3ss.studio.registry_api import get_registry_status_payload
from namel3ss.studio.memory_agreement_api import apply_agreement_action_payload, get_agreements_payload
from namel3ss.studio.memory_rules_api import get_rules_payload, propose_rule_payload
from namel3ss.studio.routes.core import (
    handle_action,
    handle_edit,
    handle_reset,
    handle_theme,
    handle_tool_wizard,
    handle_tools_auto_bind,
)
from namel3ss.studio.routes.editor import (
    handle_editor_apply,
    handle_editor_diagnose,
    handle_editor_fix,
    handle_editor_rename,
)
from namel3ss.studio.routes.packs import (
    handle_pack_add,
    handle_pack_disable,
    handle_pack_enable,
    handle_pack_verify,
)
from namel3ss.studio.routes.registry import handle_discover, handle_pack_install, handle_registry_add
from namel3ss.studio.routes.security import handle_security_override, handle_security_sandbox
from namel3ss.studio.routes.trust import handle_trust_verify
from namel3ss.studio.security_api import get_security_payload
from namel3ss.studio.trust_api import (
    get_trust_explain_payload,
    get_trust_observe_payload,
    get_trust_proof_payload,
    get_trust_secrets_payload,
    get_trust_summary_payload,
)
from namel3ss.studio.why_api import get_why_payload


def handle_api_get(handler: Any) -> None:
    try:
        source = handler._read_source()
    except Exception as err:  # pragma: no cover - IO error edge
        payload = build_error_payload(f"Cannot read source: {err}", kind="engine")
        handler._respond_json(payload, status=500)
        return
    if handler.path == "/api/summary":
        _respond_with_source(handler, source, get_summary_payload, kind="parse", include_app_path=True)
        return
    if handler.path == "/api/ui":
        _respond_with_source(handler, source, get_ui_payload, kind="manifest", include_session=True)
        return
    if handler.path == "/api/actions":
        _respond_with_source(handler, source, get_actions_payload, kind="manifest")
        return
    if handler.path == "/api/lint":
        payload = get_lint_payload(source)
        handler._respond_json(payload, status=200)
        return
    if handler.path == "/api/tools":
        _respond_with_source(handler, source, get_tools_payload, kind="tools", include_app_path=True)
        return
    if handler.path == "/api/packs":
        payload = get_packs_payload(handler.server.app_path)  # type: ignore[attr-defined]
        handler._respond_json(payload, status=200 if payload.get("ok", True) else 400)
        return
    if handler.path == "/api/registry/status":
        payload = get_registry_status_payload(handler.server.app_path)  # type: ignore[attr-defined]
        handler._respond_json(payload, status=200 if payload.get("ok", True) else 400)
        return
    if handler.path == "/api/security":
        payload = get_security_payload(handler.server.app_path)  # type: ignore[attr-defined]
        handler._respond_json(payload, status=200 if payload.get("ok", True) else 400)
        return
    if handler.path == "/api/memory/agreements":
        payload = get_agreements_payload(handler.server.app_path, handler._get_session())  # type: ignore[attr-defined]
        handler._respond_json(payload, status=200 if payload.get("ok", True) else 400)
        return
    if handler.path == "/api/memory/rules":
        payload = get_rules_payload(handler.server.app_path, handler._get_session())  # type: ignore[attr-defined]
        handler._respond_json(payload, status=200 if payload.get("ok", True) else 400)
        return
    if handler.path == "/api/graph":
        _respond_simple(handler, source, get_graph_payload, kind="graph")
        return
    if handler.path == "/api/exports":
        _respond_simple(handler, source, get_exports_payload, kind="exports")
        return
    if handler.path == "/api/trust/summary":
        _respond_simple(handler, source, get_trust_summary_payload, kind="trust")
        return
    if handler.path == "/api/trust/proof":
        _respond_simple(handler, source, get_trust_proof_payload, kind="trust", allow_error=True)
        return
    if handler.path == "/api/trust/secrets":
        _respond_simple(handler, source, get_trust_secrets_payload, kind="trust")
        return
    if handler.path.startswith("/api/trust/observe"):
        params = _query_params(handler.path)
        since = _first_param(params, "since")
        limit = _int_param(params, "limit", default=50)
        try:
            payload = get_trust_observe_payload(handler.server.app_path, since=since, limit=limit)  # type: ignore[attr-defined]
            handler._respond_json(payload, status=200)
            return
        except Namel3ssError as err:
            payload = build_error_from_exception(err, kind="trust", source=source)
            handler._respond_json(payload, status=400)
            return
    if handler.path == "/api/trust/explain":
        _respond_simple(handler, source, get_trust_explain_payload, kind="trust")
        return
    if handler.path == "/api/why":
        _respond_simple(handler, source, get_why_payload, kind="why")
        return
    if handler.path == "/api/data/summary":
        _respond_simple(handler, source, get_data_summary_payload, kind="data")
        return
    if handler.path.startswith("/api/audit"):
        params = _query_params(handler.path)
        since = _first_param(params, "since")
        limit = _int_param(params, "limit", default=50)
        filter_text = _first_param(params, "filter")
        try:
            payload = get_audit_payload(
                handler.server.app_path, since=since, limit=limit, filter_text=filter_text  # type: ignore[attr-defined]
            )
            handler._respond_json(payload, status=200)
            return
        except Namel3ssError as err:
            payload = build_error_from_exception(err, kind="audit", source=source)
            handler._respond_json(payload, status=400)
            return
    if handler.path.startswith("/api/pkg/search"):
        params = _query_params(handler.path)
        query = _first_param(params, "q") or ""
        payload = search_pkg_index_payload(query)
        handler._respond_json(payload, status=200 if payload.get("ok", True) else 400)
        return
    if handler.path.startswith("/api/pkg/info"):
        params = _query_params(handler.path)
        name = _first_param(params, "name") or ""
        payload = get_pkg_info_payload(name)
        handler._respond_json(payload, status=200 if payload.get("ok", True) else 400)
        return
    if handler.path == "/api/version":
        from namel3ss.studio.api import get_version_payload

        payload = get_version_payload()
        handler._respond_json(payload, status=200)
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
    if handler.path == "/api/edit":
        handle_edit(handler, source, body)
        return
    if handler.path == "/api/action":
        handle_action(handler, source, body)
        return
    if handler.path == "/api/tool-wizard":
        handle_tool_wizard(handler, source, body)
        return
    if handler.path == "/api/theme":
        handle_theme(handler, source, body)
        return
    if handler.path == "/api/reset":
        handle_reset(handler)
        return
    if handler.path == "/api/memory/agreements/approve":
        proposal_id = body.get("proposal_id")
        payload = apply_agreement_action_payload(
            handler.server.app_path,  # type: ignore[attr-defined]
            handler._get_session(),
            action="approve",
            proposal_id=str(proposal_id) if proposal_id else None,
        )
        handler._respond_json(payload, status=200 if payload.get("ok", True) else 400)
        return
    if handler.path == "/api/memory/agreements/reject":
        proposal_id = body.get("proposal_id")
        payload = apply_agreement_action_payload(
            handler.server.app_path,  # type: ignore[attr-defined]
            handler._get_session(),
            action="reject",
            proposal_id=str(proposal_id) if proposal_id else None,
        )
        handler._respond_json(payload, status=200 if payload.get("ok", True) else 400)
        return
    if handler.path == "/api/memory/rules/propose":
        text = body.get("text") or ""
        scope = body.get("scope") or "team"
        priority = body.get("priority") or 0
        payload = propose_rule_payload(
            handler.server.app_path,  # type: ignore[attr-defined]
            handler._get_session(),
            text=str(text),
            scope=str(scope),
            priority=int(priority),
        )
        handler._respond_json(payload, status=200 if payload.get("ok", True) else 400)
        return
    if handler.path == "/api/tools/auto-bind":
        handle_tools_auto_bind(handler, source, body)
        return
    if handler.path == "/api/packs/add":
        handle_pack_add(handler, source, body)
        return
    if handler.path == "/api/packs/verify":
        handle_pack_verify(handler, source, body)
        return
    if handler.path == "/api/packs/enable":
        handle_pack_enable(handler, source, body)
        return
    if handler.path == "/api/packs/disable":
        handle_pack_disable(handler, source, body)
        return
    if handler.path == "/api/registry/add_bundle":
        handle_registry_add(handler, source, body)
        return
    if handler.path == "/api/discover":
        handle_discover(handler, source, body)
        return
    if handler.path == "/api/packs/install":
        handle_pack_install(handler, source, body)
        return
    if handler.path == "/api/security/override":
        handle_security_override(handler, source, body)
        return
    if handler.path == "/api/security/sandbox":
        handle_security_sandbox(handler, source, body)
        return
    if handler.path == "/api/trust/verify":
        handle_trust_verify(handler, source, body)
        return
    if handler.path == "/api/editor/diagnose":
        handle_editor_diagnose(handler, source, body)
        return
    if handler.path == "/api/editor/fix":
        handle_editor_fix(handler, source, body)
        return
    if handler.path == "/api/editor/rename":
        handle_editor_rename(handler, source, body)
        return
    if handler.path == "/api/editor/apply":
        handle_editor_apply(handler, source, body)
        return
    handler.send_error(404)


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


def _query_params(path: str) -> dict:
    parsed = urlparse(path)
    return parse_qs(parsed.query or "")


def _first_param(params: dict, key: str) -> str | None:
    values = params.get(key)
    if not values:
        return None
    return str(values[0]) if values[0] is not None else None


def _int_param(params: dict, key: str, *, default: int) -> int:
    raw = _first_param(params, key)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


__all__ = ["handle_api_get", "handle_api_post"]
