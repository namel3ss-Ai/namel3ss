from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

from namel3ss.config.loader import load_config
from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.executor import execute_program_flow
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


@dataclass(frozen=True)
class RouteDispatchResult:
    payload: dict | None
    status: int
    headers: dict[str, str] | None = None
    body: bytes | None = None
    content_type: str | None = None


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
    match = registry.match(method, parsed.path)
    if match is None:
        return None
    entry = match.entry
    enforce_route_permissions(entry, identity=identity, auth_context=auth_context)
    query = parse_qs(parsed.query or "")
    query_values = query_params(query)
    try:
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
            identity=identity,
            auth_context=auth_context,
            store=store,
            conventions=conventions,
        )
        if format_name == "toon":
            token = encode_toon(payload)
            return RouteDispatchResult(
                payload=None,
                body=token.encode("utf-8"),
                content_type="text/plain; charset=utf-8",
                status=200,
            )
        return RouteDispatchResult(payload=payload, status=200)
    except Namel3ssError as err:
        return RouteDispatchResult(
            payload=build_error_envelope(error=err, project_root=getattr(program, "project_root", None)),
            status=_status_from_error(err),
        )
    except Exception as err:  # pragma: no cover - defensive guard rail
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
) -> dict:
    entry = match.entry
    list_fields = _list_response_fields(entry.response or {})
    route_conventions = conventions.for_route(entry.name)
    input_data: dict[str, object] = {}
    input_data.update(coerce_params(match.path_params, entry.parameters))
    filtered_query = {
        key: value
        for key, value in query_values.items()
        if key not in {"page", "page_size", "filter", "format"}
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
    return response


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
