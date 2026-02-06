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
from namel3ss.governance.audit import record_audit_entry, resolve_actor
from namel3ss.federation.tenants import resolve_request_tenant
from namel3ss.runtime.router.federation import (
    build_federation_context,
    federation_audit_details,
    record_federated_usage,
    validate_federated_input,
    validate_federated_output_schema,
)
from namel3ss.runtime.router.messages import (
    deprecated_headers,
    deprecation_warning,
    error_reason_code,
    filter_not_allowed_message,
    format_not_allowed_message,
    log_deprecated_route_call,
    removed_version_message,
    requested_version,
    status_from_error,
)
from namel3ss.runtime.router.streaming import (
    build_sse_body,
    should_stream_response,
    sorted_yield_messages,
)


@dataclass(frozen=True)
class RouteDispatchResult:
    payload: dict | None
    status: int
    headers: dict[str, str] | None = None
    body: bytes | None = None
    content_type: str | None = None


@dataclass(frozen=True)
class RouteRunPayload:
    request: dict[str, object]
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
    flow_executor=None,
) -> RouteDispatchResult | None:
    parsed = urlparse(raw_path)
    query = parse_qs(parsed.query or "")
    query_values = query_params(query)
    requested_version_value = requested_version(query_values, headers)
    match = registry.match(method, parsed.path, requested_version=requested_version_value)
    if match is None:
        if requested_version_value:
            removed = registry.removed_version(method, parsed.path, requested_version_value)
            if removed is not None:
                warning = deprecation_warning(removed)
                err = Namel3ssError(
                    removed_version_message(removed, requested_version_value),
                    details={"http_status": 404, "category": "version", "reason_code": "removed_version"},
                )
                return RouteDispatchResult(
                    payload=build_error_envelope(error=err, project_root=getattr(program, "project_root", None)),
                    status=404,
                    headers={"X-N3-Deprecation-Warning": warning},
                )
        return None
    entry = match.entry
    warning_headers = deprecated_headers(entry)
    request_identity = identity
    active_tenant = None
    actor = resolve_actor(identity, auth_context)
    federation_context = None
    federation_contract = None
    federated_bytes_in = 0
    federated_bytes_out = 0
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
        federation_context = build_federation_context(
            headers=headers,
            query_values=query_values,
            identity=request_identity,
            target_tenant=active_tenant,
        )
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
        def _federation_preflight(request_payload: dict[str, object]) -> None:
            nonlocal federation_contract, federated_bytes_in
            if federation_context is None or not federation_context.is_cross_tenant:
                return
            federation_contract, federated_bytes_in = validate_federated_input(
                project_root=getattr(program, "project_root", None),
                app_path=getattr(program, "app_path", None),
                context=federation_context,
                flow_name=entry.flow_name,
                input_payload=request_payload,
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
            before_execute=_federation_preflight,
            flow_executor=flow_executor,
        )
        if federation_context is not None and federation_context.is_cross_tenant:
            if federation_contract is not None:
                federated_bytes_out = validate_federated_output_schema(federation_contract, payload.response)
            record_federated_usage(
                project_root=getattr(program, "project_root", None),
                app_path=getattr(program, "app_path", None),
                contract=federation_contract,
                status="success",
                bytes_in=federated_bytes_in,
                bytes_out=federated_bytes_out,
            )
        if should_stream_response(query_values, headers, payload.yield_messages):
            if warning_headers:
                log_deprecated_route_call(program, entry, requested_version=requested_version_value)
            stream_headers = dict(warning_headers or {})
            stream_headers["Cache-Control"] = "no-cache"
            _record_route_audit(
                program,
                entry,
                user=actor,
                status="success",
                details={
                    "stream": True,
                    "requested_version": requested_version_value or "",
                    "tenant_id": active_tenant or "",
                    **federation_audit_details(
                        context=federation_context,
                        contract=federation_contract,
                        bytes_in=federated_bytes_in,
                        bytes_out=federated_bytes_out,
                    ),
                },
            )
            return RouteDispatchResult(
                payload=None,
                body=build_sse_body(payload.yield_messages, payload.response),
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
                details={
                    "format": "toon",
                    "requested_version": requested_version_value or "",
                    "tenant_id": active_tenant or "",
                    **federation_audit_details(
                        context=federation_context,
                        contract=federation_contract,
                        bytes_in=federated_bytes_in,
                        bytes_out=federated_bytes_out,
                    ),
                },
            )
            return RouteDispatchResult(
                payload=None,
                body=token.encode("utf-8"),
                content_type="text/plain; charset=utf-8",
                status=200,
                headers=warning_headers,
            )
        if warning_headers:
            log_deprecated_route_call(program, entry, requested_version=requested_version_value)
        _record_route_audit(
            program,
            entry,
            user=actor,
            status="success",
            details={
                "requested_version": requested_version_value or "",
                "tenant_id": active_tenant or "",
                **federation_audit_details(
                    context=federation_context,
                    contract=federation_contract,
                    bytes_in=federated_bytes_in,
                    bytes_out=federated_bytes_out,
                ),
            },
        )
        return RouteDispatchResult(payload=payload.response, status=200, headers=warning_headers)
    except Namel3ssError as err:
        if federation_context is not None and federation_context.is_cross_tenant:
            record_federated_usage(
                project_root=getattr(program, "project_root", None),
                app_path=getattr(program, "app_path", None),
                contract=federation_contract,
                status="failure",
                bytes_in=federated_bytes_in,
                bytes_out=federated_bytes_out,
                error=str(err),
            )
        _record_route_audit(
            program,
            entry,
            user=actor,
            status="failure",
            details={
                "reason_code": error_reason_code(err),
                "http_status": status_from_error(err),
                "requested_version": requested_version_value or "",
                "tenant_id": active_tenant or "",
                **federation_audit_details(
                    context=federation_context,
                    contract=federation_contract,
                    bytes_in=federated_bytes_in,
                    bytes_out=federated_bytes_out,
                ),
            },
        )
        return RouteDispatchResult(
            payload=build_error_envelope(error=err, project_root=getattr(program, "project_root", None)),
            status=status_from_error(err),
        )
    except Exception as err:  # pragma: no cover - defensive guard rail
        if federation_context is not None and federation_context.is_cross_tenant:
            record_federated_usage(
                project_root=getattr(program, "project_root", None),
                app_path=getattr(program, "app_path", None),
                contract=federation_contract,
                status="failure",
                bytes_in=federated_bytes_in,
                bytes_out=federated_bytes_out,
                error=str(err),
            )
        _record_route_audit(
            program,
            entry,
            user=actor,
            status="failure",
            details={
                "reason_code": "internal_error",
                "requested_version": requested_version_value or "",
                "tenant_id": active_tenant or "",
                **federation_audit_details(
                    context=federation_context,
                    contract=federation_contract,
                    bytes_in=federated_bytes_in,
                    bytes_out=federated_bytes_out,
                ),
            },
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
    before_execute=None,
    flow_executor=None,
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
                    filter_not_allowed_message(entry.name),
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
    if callable(before_execute):
        before_execute(dict(input_data))
    execute = flow_executor if callable(flow_executor) else execute_program_flow
    result = execute(
        program=program,
        flow_name=entry.flow_name,
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
        request=dict(input_data),
        response=response,
        yield_messages=sorted_yield_messages(getattr(result, "yield_messages", None)),
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
            format_not_allowed_message(route_name, requested),
            details={"http_status": 406, "category": "format", "reason_code": "format_not_allowed"},
        )
    return requested

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
