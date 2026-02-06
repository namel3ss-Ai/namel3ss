from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from namel3ss.config.loader import load_config
from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.executor import execute_program_flow
from namel3ss.runtime.persistence_paths import resolve_persistence_root
from namel3ss.runtime.router.registry import RouteEntry, RouteMatch, RouteRegistry
from namel3ss.runtime.router.request import coerce_params, query_params, read_json_body
from namel3ss.runtime.router.authorization import enforce_route_permissions
from namel3ss.runtime.router.upload import handle_route_upload, register_dataset
from namel3ss.runtime.conventions.config import load_conventions_config
from namel3ss.runtime.conventions.errors import build_error_envelope
from namel3ss.runtime.conventions.filters import apply_filters, parse_filter_param
from namel3ss.runtime.conventions.formats import load_formats_config
from namel3ss.runtime.conventions.pagination import apply_pagination, parse_pagination
from namel3ss.runtime.conventions.toon import encode_toon
from namel3ss.governance.audit import record_audit_entry, resolve_actor
from namel3ss.federation.tenants import resolve_request_tenant


@dataclass(frozen=True)
class RouteDispatchResult:
    payload: dict | None
    status: int
    headers: dict[str, str] | None = None
    body: bytes | None = None
    content_type: str | None = None


@dataclass(frozen=True)
class RouteRunPayload:
    response: dict
    yield_messages: list[dict]


def dispatch_route(
    *,
    registry: RouteRegistry,
    method: str,
    raw_path: str,
    headers: dict[str, str],
    rfile,
    program,
    identity: dict | None,
    auth_context: object | None,
    store,
) -> RouteDispatchResult | None:
    parsed = urlparse(raw_path)
    query = parse_qs(parsed.query or "")
    query_values = query_params(query)
    requested_version = _requested_version(query_values, headers)
    match = registry.match(method, parsed.path, requested_version=requested_version)
    if match is None:
        if requested_version:
            removed = registry.removed_version(method, parsed.path, requested_version)
            if removed is not None:
                warning = _deprecation_warning(removed)
                err = Namel3ssError(
                    _removed_version_message(removed, requested_version),
                    details={"http_status": 404, "category": "version", "reason_code": "removed_version"},
                )
                return RouteDispatchResult(
                    payload=build_error_envelope(error=err, project_root=getattr(program, "project_root", None)),
                    status=404,
                    headers={"X-N3-Deprecation-Warning": warning},
                )
        return None
    entry = match.entry
    warning_headers = _deprecated_headers(entry)
    request_identity = identity
    active_tenant = None
    actor = resolve_actor(identity, auth_context)
    try:
        active_tenant = resolve_request_tenant(
            headers=headers,
            query_values=query_values,
            identity=identity,
            project_root=getattr(program, "project_root", None),
            app_path=getattr(program, "app_path", None),
        )
        if active_tenant:
            request_identity = dict(identity or {})
            request_identity.setdefault("tenant", active_tenant)
            request_identity.setdefault("tenant_id", active_tenant)
        actor = resolve_actor(request_identity, auth_context)
        enforce_route_permissions(entry, identity=request_identity, auth_context=auth_context)
        formats_config = load_formats_config(
            getattr(program, "project_root", None),
            getattr(program, "app_path", None),
        )
        format_name = _resolve_response_format(entry.name, query_values, headers, formats_config)
        conventions = load_conventions_config(
            getattr(program, "project_root", None),
            getattr(program, "app_path", None),
        )
        payload = _run_route(
            match=match,
            query=query,
            query_values=query_values,
            headers=headers,
            rfile=rfile,
            program=program,
            identity=request_identity,
            auth_context=auth_context,
            store=store,
            conventions=conventions,
        )
        if _should_stream_response(query_values, headers, payload.yield_messages):
            if warning_headers:
                _log_deprecated_route_call(program, entry, requested_version=requested_version)
            stream_headers = dict(warning_headers or {})
            stream_headers["Cache-Control"] = "no-cache"
            _record_route_audit(
                program,
                entry,
                user=actor,
                status="success",
                details={"stream": True, "requested_version": requested_version or "", "tenant_id": active_tenant or ""},
            )
            return RouteDispatchResult(
                payload=None,
                body=_build_sse_body(payload.yield_messages, payload.response),
                content_type="text/event-stream; charset=utf-8",
                status=200,
                headers=stream_headers,
            )
        if format_name == "toon":
            token = encode_toon(payload.response)
            _record_route_audit(
                program,
                entry,
                user=actor,
                status="success",
                details={"format": "toon", "requested_version": requested_version or "", "tenant_id": active_tenant or ""},
            )
            return RouteDispatchResult(
                payload=None,
                body=token.encode("utf-8"),
                content_type="text/plain; charset=utf-8",
                status=200,
                headers=warning_headers,
            )
        if warning_headers:
            _log_deprecated_route_call(program, entry, requested_version=requested_version)
        _record_route_audit(
            program,
            entry,
            user=actor,
            status="success",
            details={"requested_version": requested_version or "", "tenant_id": active_tenant or ""},
        )
        return RouteDispatchResult(payload=payload.response, status=200, headers=warning_headers)
    except Namel3ssError as err:
        _record_route_audit(
            program,
            entry,
            user=actor,
            status="failure",
            details={
                "reason_code": _error_reason_code(err),
                "http_status": _status_from_error(err),
                "requested_version": requested_version or "",
                "tenant_id": active_tenant or "",
            },
        )
        return RouteDispatchResult(
            payload=build_error_envelope(error=err, project_root=getattr(program, "project_root", None)),
            status=_status_from_error(err),
        )
    except Exception as err:  # pragma: no cover - defensive guard rail
        _record_route_audit(
            program,
            entry,
            user=actor,
            status="failure",
            details={"reason_code": "internal_error", "requested_version": requested_version or "", "tenant_id": active_tenant or ""},
        )
        return RouteDispatchResult(
            payload=build_error_envelope(error=err, project_root=getattr(program, "project_root", None)),
            status=500,
        )


def _run_route(
    *,
    match: RouteMatch,
    query: dict[str, list[str]],
    query_values: dict[str, str],
    headers: dict[str, str],
    rfile,
    program,
    identity: dict | None,
    auth_context: object | None,
    store,
    conventions,
) -> RouteRunPayload:
    entry = match.entry
    list_fields = _list_response_fields(entry.response or {})
    route_conventions = conventions.for_route(entry.name)
    input_data: dict[str, object] = {}
    input_data.update(coerce_params(match.path_params, entry.parameters))
    filtered_query = {
        key: value
        for key, value in query_values.items()
        if key not in {"page", "page_size", "filter", "format", "version"}
    }
    input_data.update(coerce_params(filtered_query, entry.parameters))
    filters: dict[str, str] = {}
    if list_fields:
        filter_value = query_values.get("filter")
        if filter_value:
            if not route_conventions.filter_fields:
                raise Namel3ssError(
                    _filter_not_allowed_message(entry.name),
                    details={"http_status": 400, "category": "filter", "reason_code": "filter_not_allowed"},
                )
            filters = parse_filter_param(
                filter_value,
                allowed_fields=route_conventions.filter_fields,
                route_name=entry.name,
            )
            input_data["filter"] = dict(filters)
        if route_conventions.pagination:
            page, page_size = parse_pagination(
                query_values,
                conventions=route_conventions,
                route_name=entry.name,
            )
            input_data["page"] = page
            input_data["page_size"] = page_size
    upload_metadata: dict | None = None
    if entry.upload:
        upload_metadata = handle_route_upload(headers, rfile, program)
        if upload_metadata:
            input_data["upload_id"] = upload_metadata.get("checksum")
            input_data["upload"] = upload_metadata
            register_dataset(upload_metadata, program, identity, auth_context)
    body_payload = {} if entry.upload or entry.request is None else read_json_body(headers, rfile)
    if body_payload:
        input_data.update(body_payload)
    result = execute_program_flow(
        program,
        entry.flow_name,
        input=input_data,
        store=store,
        identity=identity,
        auth_context=auth_context,
        route_name=entry.name,
        config=load_config(
            app_path=getattr(program, "app_path", None),
            root=getattr(program, "project_root", None),
        ),
    )
    response = _format_response(entry, result.last_value)
    if list_fields:
        response = apply_filters(response, list_fields=list_fields, filters=filters)
        if route_conventions.pagination:
            page = int(input_data.get("page") or 1)
            page_size = int(input_data.get("page_size") or route_conventions.page_size_default)
            response, has_more = apply_pagination(
                response,
                list_fields=list_fields,
                page=page,
                page_size=page_size,
            )
            if has_more and "next_page" not in response:
                response["next_page"] = page + 1
    if upload_metadata and "upload_id" not in response:
        response["upload_id"] = upload_metadata.get("checksum")
    return RouteRunPayload(
        response=response,
        yield_messages=_sorted_yield_messages(getattr(result, "yield_messages", None)),
    )


def _format_response(entry: RouteEntry, value: object) -> dict:
    if isinstance(value, dict):
        return value
    response_fields = list(entry.response.keys()) if entry.response else []
    if len(response_fields) == 1:
        return {response_fields[0]: value}
    if not response_fields:
        return {"result": value}
    raise Namel3ssError("Flow response must be an object matching the route response schema.")


def _list_response_fields(fields: dict) -> tuple[str, ...]:
    if not fields:
        return ()
    names: list[str] = []
    for name, field in fields.items():
        type_name = getattr(field, "type_name", "")
        if isinstance(type_name, str) and type_name.startswith("list<"):
            names.append(name)
    return tuple(sorted(names))


def _resolve_response_format(route_name: str, query: dict[str, str], headers: dict[str, str], formats) -> str:
    requested = None
    if "format" in query:
        requested = str(query.get("format") or "").strip().lower()
    if not requested:
        accept = headers.get("Accept") or headers.get("accept") or ""
        lowered = accept.lower()
        if "toon" in lowered:
            requested = "toon"
    if not requested:
        requested = "json"
    allowed = formats.formats_for_route(route_name)
    if requested not in allowed:
        raise Namel3ssError(
            _format_not_allowed_message(route_name, requested),
            details={"http_status": 406, "category": "format", "reason_code": "format_not_allowed"},
        )
    return requested


def _format_not_allowed_message(route_name: str, requested: str) -> str:
    return (
        f'Format "{requested}" is not available for route "{route_name}".\n'
        "Why: The route only supports configured formats.\n"
        "Fix: Request a supported format or update formats.yaml.\n"
        "Example: format=json"
    )


def _filter_not_allowed_message(route_name: str) -> str:
    return (
        f'Filters are not enabled for route "{route_name}".\n'
        "Why: No filter fields are configured.\n"
        "Fix: Add filter_fields in conventions.yaml or remove the filter parameter.\n"
        "Example: filter=status:open"
    )


def _requested_version(query: dict[str, str], headers: dict[str, str]) -> str | None:
    query_value = str(query.get("version") or "").strip()
    if query_value:
        return query_value
    header_value = str(headers.get("Accept-Version") or headers.get("accept-version") or "").strip()
    return header_value or None


def _deprecated_headers(entry: RouteEntry) -> dict[str, str] | None:
    if entry.status != "deprecated":
        return None
    return {"X-N3-Deprecation-Warning": _deprecation_warning(entry)}


def _deprecation_warning(entry: RouteEntry) -> str:
    message = f'route "{entry.entity_name}" version "{entry.version or "default"}" is deprecated'
    if entry.replacement:
        message += f'; use "{entry.replacement}"'
    if entry.deprecation_date:
        message += f"; end_of_life={entry.deprecation_date}"
    return message


def _removed_version_message(entry: RouteEntry, requested_version: str) -> str:
    if entry.replacement:
        return (
            f'Route "{entry.entity_name}" version "{requested_version}" was removed. '
            f'Use version "{entry.replacement}" instead.'
        )
    return f'Route "{entry.entity_name}" version "{requested_version}" was removed.'


def _log_deprecated_route_call(program, entry: RouteEntry, *, requested_version: str | None) -> None:
    root = resolve_persistence_root(getattr(program, "project_root", None), getattr(program, "app_path", None))
    if root is None:
        return
    log_path = Path(root) / ".namel3ss" / "deprecations.jsonl"
    row = {
        "route_name": entry.name,
        "entity_name": entry.entity_name,
        "version": entry.version or "default",
        "status": entry.status,
        "replacement": entry.replacement or "",
        "deprecation_date": entry.deprecation_date or "",
        "requested_version": requested_version or "",
    }
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(canonical_json_dumps(row, pretty=False, drop_run_keys=False) + "\n")


def _status_from_error(err: Namel3ssError) -> int:
    details = err.details if isinstance(err.details, dict) else {}
    status = details.get("http_status")
    if isinstance(status, int):
        return status
    if isinstance(status, str) and status.isdigit():
        return int(status)
    category = details.get("category")
    if category == "authentication":
        return 401
    if category == "permission":
        return 403
    return 400


def _error_reason_code(err: Namel3ssError) -> str:
    details = err.details if isinstance(err.details, dict) else {}
    reason = details.get("reason_code")
    if isinstance(reason, str) and reason.strip():
        return reason.strip()
    category = details.get("category")
    if isinstance(category, str) and category.strip():
        return category.strip()
    return "request_error"


def _record_route_audit(program, entry: RouteEntry, *, user: str, status: str, details: dict[str, object]) -> None:
    record_audit_entry(
        project_root=getattr(program, "project_root", None),
        app_path=getattr(program, "app_path", None),
        user=user,
        action="invoke_route",
        resource=entry.name,
        status=status,
        details={
            "flow_name": entry.flow_name,
            "method": entry.method,
            "path": entry.path,
            **details,
        },
    )


def _should_stream_response(query: dict[str, str], headers: dict[str, str], yield_messages: list[dict]) -> bool:
    if yield_messages:
        return True
    stream = str(query.get("stream") or "").strip().lower()
    if stream in {"1", "true", "yes", "on"}:
        return True
    accept = str(headers.get("Accept") or headers.get("accept") or "").lower()
    if "text/event-stream" in accept:
        return True
    header_stream = str(headers.get("X-N3-Stream") or headers.get("x-n3-stream") or "").strip().lower()
    return header_stream in {"1", "true", "yes", "on"}


def _build_sse_body(yield_messages: list[dict], response: dict) -> bytes:
    lines: list[str] = []
    for message in yield_messages:
        lines.append("event: yield")
        lines.append(f"data: {canonical_json_dumps(message, pretty=False, drop_run_keys=False)}")
        lines.append("")
    lines.append("event: return")
    lines.append(f"data: {canonical_json_dumps(response, pretty=False, drop_run_keys=False)}")
    lines.append("")
    return "\n".join(lines).encode("utf-8")


def _sorted_yield_messages(raw: object) -> list[dict]:
    if not isinstance(raw, list):
        return []
    rows: list[dict] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        sequence = _safe_int(item.get("sequence"))
        flow_name = str(item.get("flow_name") or "")
        payload = {
            "flow_name": flow_name,
            "output": item.get("output"),
            "sequence": sequence,
        }
        rows.append(payload)
    rows.sort(
        key=lambda entry: (
            int(entry.get("sequence") or 0),
            str(entry.get("flow_name") or ""),
            canonical_json_dumps(entry.get("output"), pretty=False, drop_run_keys=False),
        )
    )
    return rows


def _safe_int(value: object) -> int:
    if isinstance(value, bool):
        return 0
    try:
        parsed = int(value)
    except Exception:
        return 0
    if parsed < 0:
        return 0
    return parsed
