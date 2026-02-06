from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from namel3ss.config.loader import load_config
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.payload import build_error_payload
from namel3ss.runtime.auth.auth_context import resolve_auth_context
from namel3ss.runtime.backend.document_handler import handle_document_page, handle_document_pdf
from namel3ss.runtime.server.dev.errors import error_from_exception, error_from_message

from . import core


def handle_documents_get(handler: Any, raw_path: str) -> bool:
    parsed_url = urlparse(raw_path)
    parsed = _parse_document_path(parsed_url.path)
    if parsed is None:
        return False
    state = handler._state()
    state._refresh_if_needed()
    program = state.program
    if program is None:
        payload = build_error_payload("Program not loaded.", kind="engine")
        handler._respond_json(payload, status=500)
        return True
    auth_context = _auth_context_or_error(handler, kind="engine")
    if auth_context is None:
        return True
    query = parse_qs(parsed_url.query or "")
    chunk_id = _query_value(query, "chunk_id") or _query_value(query, "chunk")
    ctx = SimpleNamespace(
        capabilities=getattr(program, "capabilities", ()),
        project_root=getattr(program, "project_root", None),
        app_path=getattr(program, "app_path", None),
    )
    runtime_state = getattr(state, "session", None)
    state_value = getattr(runtime_state, "state", None) if runtime_state is not None else None
    document_id = parsed["document_id"]
    identity = getattr(auth_context, "identity", None)
    policy_decl = getattr(program, "policy", None)
    if parsed["kind"] == "pdf":
        try:
            content, _info, filename = handle_document_pdf(
                ctx,
                document_id=document_id,
                identity=identity,
                policy_decl=policy_decl,
            )
            headers = {"Content-Disposition": f'inline; filename="{filename}"'}
            core.respond_bytes(handler, content, content_type="application/pdf", headers=headers)
        except Namel3ssError as err:
            payload = error_from_exception(
                err,
                kind="engine",
                source=state._source_payload(),
                mode=handler._mode(),
                debug=state.debug,
            )
            handler._respond_json(payload, status=400)
        except Exception as err:  # pragma: no cover - defensive guard
            payload = error_from_message(
                str(err),
                kind="internal",
                mode=handler._mode(),
                debug=state.debug,
            )
            handler._respond_json(payload, status=500)
        return True
    try:
        response = handle_document_page(
            ctx,
            document_id=document_id,
            page_number=parsed["page_number"],
            state=state_value if isinstance(state_value, dict) else None,
            chunk_id=chunk_id,
            identity=identity,
            policy_decl=policy_decl,
        )
        handler._respond_json(response, status=200)
    except Namel3ssError as err:
        payload = error_from_exception(
            err,
            kind="engine",
            source=state._source_payload(),
            mode=handler._mode(),
            debug=state.debug,
        )
        handler._respond_json(payload, status=400)
    except Exception as err:  # pragma: no cover - defensive guard
        payload = error_from_message(
            str(err),
            kind="internal",
            mode=handler._mode(),
            debug=state.debug,
        )
        handler._respond_json(payload, status=500)
    return True


def _parse_document_path(path: str) -> dict | None:
    if not path.startswith("/api/documents/"):
        return None
    parts = [part for part in path.split("/") if part]
    if len(parts) == 4 and parts[0] == "api" and parts[1] == "documents" and parts[3] == "pdf":
        document_id = unquote(parts[2])
        if document_id:
            return {"kind": "pdf", "document_id": document_id}
    if len(parts) == 5 and parts[0] == "api" and parts[1] == "documents" and parts[3] == "pages":
        document_id = unquote(parts[2])
        page_number = unquote(parts[4])
        if document_id and page_number:
            return {"kind": "page", "document_id": document_id, "page_number": page_number}
    return None


def _query_value(query: dict, key: str) -> str | None:
    values = query.get(key)
    if not isinstance(values, list):
        return None
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _auth_context_or_error(handler: Any, *, kind: str) -> object | None:
    state = handler._state()
    state._refresh_if_needed()
    program = state.program
    try:
        config = load_config(app_path=state.app_path)
        store = state.session.ensure_store(config)
        identity_schema = getattr(program, "identity", None) if program is not None else None
        return resolve_auth_context(
            dict(handler.headers.items()),
            config=config,
            identity_schema=identity_schema,
            store=store,
            project_root=str(getattr(program, "project_root", "") or "") or None,
            app_path=str(getattr(program, "app_path", "") or "") or None,
        )
    except Namel3ssError as err:
        payload = error_from_exception(
            err,
            kind=kind,
            source=state._source_payload(),
            mode=handler._mode(),
            debug=state.debug,
        )
        handler._respond_json(payload, status=400)
        return None


__all__ = ["handle_documents_get"]
