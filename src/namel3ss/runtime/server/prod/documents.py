from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from urllib.parse import unquote

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.payload import build_error_from_exception, build_error_payload
from namel3ss.runtime.backend.document_handler import handle_document_page, handle_document_pdf


def handle_documents_get(handler: Any, path: str) -> bool:
    parsed = _parse_document_path(path)
    if parsed is None:
        return False
    program = getattr(handler._state(), "program", None)
    if program is None:
        payload = build_error_payload("Program not loaded.", kind="engine")
        handler._respond_json(payload, status=500)
        return True
    auth_context = handler._auth_context_or_error(kind="engine")
    if auth_context is None:
        return True
    ctx = SimpleNamespace(
        capabilities=getattr(program, "capabilities", ()),
        project_root=getattr(program, "project_root", None),
        app_path=getattr(program, "app_path", None),
    )
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
            handler._respond_bytes(content, content_type="application/pdf", headers=headers)
        except Namel3ssError as err:
            payload = build_error_from_exception(err, kind="engine")
            handler._respond_json(payload, status=400)
        except Exception as err:  # pragma: no cover - defensive guard rail
            payload = build_error_payload(str(err), kind="internal")
            handler._respond_json(payload, status=500)
        return True
    try:
        response = handle_document_page(
            ctx,
            document_id=document_id,
            page_number=parsed["page_number"],
            identity=identity,
            policy_decl=policy_decl,
        )
        handler._respond_json(response, status=200)
    except Namel3ssError as err:
        payload = build_error_from_exception(err, kind="engine")
        handler._respond_json(payload, status=400)
    except Exception as err:  # pragma: no cover - defensive guard rail
        payload = build_error_payload(str(err), kind="internal")
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


__all__ = ["handle_documents_get"]
