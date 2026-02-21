from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.payload import build_error_payload
from namel3ss.resources import package_root, studio_web_root
from namel3ss.ui.external.serve import resolve_builtin_icon_file, resolve_external_ui_file


def read_json_body(handler: Any) -> dict | None:
    length = int(handler.headers.get("Content-Length", "0"))
    raw_body = handler.rfile.read(length) if length else b""
    if not raw_body:
        return {}
    try:
        decoded = raw_body.decode("utf-8")
        return json.loads(decoded or "{}")
    except Exception:
        return None


def respond_json(handler: Any, payload: dict, *, status: int = 200, headers: dict[str, str] | None = None) -> None:
    data = canonical_json_dumps(payload, pretty=False, drop_run_keys=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(data)))
    if headers:
        for key, value in headers.items():
            handler.send_header(key, value)
    handler.end_headers()
    handler.wfile.write(data)


def respond_bytes(
    handler: Any,
    payload: bytes,
    *,
    status: int = 200,
    content_type: str = "application/octet-stream",
    headers: dict[str, str] | None = None,
) -> None:
    handler.send_response(status)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(payload)))
    if headers:
        for key, value in headers.items():
            handler.send_header(key, value)
    handler.end_headers()
    handler.wfile.write(payload)


def handle_static(handler: Any, path: str) -> bool:
    if bool(getattr(handler.server, "headless", False)):  # type: ignore[attr-defined]
        return False
    icon_path, icon_type = resolve_builtin_icon_file(path)
    if icon_path and icon_type:
        try:
            content = icon_path.read_bytes()
        except OSError:  # pragma: no cover - IO guard
            return False
        headers = _static_cache_headers(path, icon_type)
        handler.send_response(200)
        handler.send_header("Content-Type", icon_type)
        handler.send_header("Content-Length", str(len(content)))
        for key, value in headers.items():
            handler.send_header(key, value)
        handler.end_headers()
        handler.wfile.write(content)
        return True
    file_path, content_type = _resolve_runtime_file(path, handler._mode())
    if not file_path or not content_type:
        return False
    try:
        content = file_path.read_bytes()
    except OSError:  # pragma: no cover - IO guard
        return False
    headers = _static_cache_headers(path, content_type)
    handler.send_response(200)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(content)))
    for key, value in headers.items():
        handler.send_header(key, value)
    handler.end_headers()
    handler.wfile.write(content)
    return True


def handle_observability_get(handler: Any, path: str) -> bool:
    if path == "/api/traces/runs":
        payload = _trace_runs_payload(handler)
        status = 200 if payload.get("ok", True) else 400
        handler._respond_json(payload, status=status)
        return True
    if path == "/api/traces/latest":
        payload = _trace_latest_payload(handler)
        status = 200 if payload.get("ok", True) else 404
        handler._respond_json(payload, status=status)
        return True
    if path.startswith("/api/traces/") and path not in {"/api/traces", "/api/trace"}:
        run_id = path[len("/api/traces/") :]
        payload = _trace_run_payload(handler, run_id)
        status = 200 if payload.get("ok", True) else 404
        handler._respond_json(payload, status=status)
        return True
    if path == "/api/logs":
        kind = "logs"
    elif path == "/api/traces":
        kind = "traces"
    elif path == "/api/trace":
        kind = "trace"
    elif path == "/api/metrics":
        kind = "metrics"
    else:
        return False
    payload = observability_payload(handler, kind)
    status = 200 if payload.get("ok", True) else 400
    handler._respond_json(payload, status=status)
    return True


def observability_payload(handler: Any, kind: str) -> dict:
    state = handler._state()
    state._refresh_if_needed()
    program = state.program
    if program is None:
        return build_error_payload("Program not loaded.", kind="engine")
    if not _observability_enabled():
        return _empty_observability_payload(kind)
    builder = _load_observability_builder(kind)
    if builder is None:
        return _empty_observability_payload(kind)
    return builder(getattr(program, "project_root", None), getattr(program, "app_path", None))


def _resolve_runtime_file(path: str, mode: str) -> tuple[Path | None, str | None]:
    runtime_root = _runtime_web_root()
    if path in {"/", "/index.html"}:
        filename = "dev.html" if mode == "dev" else "preview.html"
        if mode == "run":
            filename = "preview.html"
        file_path = runtime_root / filename
        if file_path.exists():
            return file_path, "text/html"
    for root in (runtime_root, studio_web_root()):
        file_path, content_type = resolve_external_ui_file(root, path)
        if file_path and content_type:
            return file_path, content_type
    return None, None


def _static_cache_headers(path: str, content_type: str) -> dict[str, str]:
    normalized_path = (path or "").lower()
    normalized_type = (content_type or "").lower()
    is_shell_html = normalized_path in {"/", "/index.html"} or normalized_type.startswith("text/html")
    is_runtime_script = normalized_path.endswith(".js")
    is_runtime_style = normalized_path.endswith(".css")
    is_icon_svg = normalized_path.startswith("/icons/") and normalized_path.endswith(".svg")
    if is_shell_html or is_runtime_script or is_runtime_style or is_icon_svg:
        return {
            "Cache-Control": "no-store, max-age=0, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        }
    return {}


def _runtime_web_root() -> Path:
    return package_root() / "runtime" / "web"


def _load_observability_builder(kind: str):
    from namel3ss.runtime import observability_api

    mapping = {
        "logs": observability_api.get_logs_payload,
        "trace": observability_api.get_trace_payload,
        "traces": observability_api.get_traces_payload,
        "metrics": observability_api.get_metrics_payload,
    }
    return mapping.get(kind)


def _observability_enabled() -> bool:
    from namel3ss.observability.enablement import observability_enabled

    return observability_enabled()


def _empty_observability_payload(kind: str) -> dict:
    if kind == "metrics":
        return {"ok": True, "counters": [], "timings": []}
    if kind in {"trace", "traces"}:
        return {"ok": True, "count": 0, "spans": []}
    return {"ok": True, "count": 0, "logs": []}


def _trace_runs_payload(handler: Any) -> dict:
    from namel3ss.runtime.observability_api import get_trace_runs_payload

    state = handler._state()
    state._refresh_if_needed()
    program = state.program
    if program is None:
        return build_error_payload("Program not loaded.", kind="engine")
    return get_trace_runs_payload(getattr(program, "project_root", None), getattr(program, "app_path", None))


def _trace_latest_payload(handler: Any) -> dict:
    from namel3ss.runtime.observability_api import get_latest_trace_run_payload

    state = handler._state()
    state._refresh_if_needed()
    program = state.program
    if program is None:
        return build_error_payload("Program not loaded.", kind="engine")
    return get_latest_trace_run_payload(getattr(program, "project_root", None), getattr(program, "app_path", None))


def _trace_run_payload(handler: Any, run_id: str) -> dict:
    from namel3ss.runtime.observability_api import get_trace_run_payload

    state = handler._state()
    state._refresh_if_needed()
    program = state.program
    if program is None:
        return build_error_payload("Program not loaded.", kind="engine")
    return get_trace_run_payload(getattr(program, "project_root", None), getattr(program, "app_path", None), run_id)


__all__ = [
    "handle_observability_get",
    "handle_static",
    "observability_payload",
    "read_json_body",
    "respond_bytes",
    "respond_json",
]
