from __future__ import annotations

import json
from urllib import request

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ir import nodes as ir
from namel3ss.runtime.backend import studio_effect_adapter
from namel3ss.runtime.secrets_store import SecretValue
from namel3ss.runtime.tools.schema_validate import validate_tool_fields
from namel3ss.utils.http_tls import safe_urlopen_with_tls_fallback
from namel3ss.utils.numbers import is_number


ALLOWED_INPUT_FIELDS = {"url", "method", "headers", "body", "timeout_seconds"}
ALLOWED_OUTPUT_FIELDS = {"status", "headers", "body", "json"}


def execute_http_tool(
    ctx,
    tool: ir.ToolDecl,
    payload: object,
    *,
    line: int | None,
    column: int | None,
) -> dict:
    _validate_http_tool_schema(tool, line=line, column=column)
    validate_tool_fields(
        fields=tool.input_fields,
        payload=payload,
        tool_name=tool.name,
        phase="input",
        line=line,
        column=column,
        type_mode="tool",
        expect_object=True,
    )
    if not isinstance(payload, dict):
        raise Namel3ssError("HTTP tool input must be an object", line=line, column=column)
    method = _read_method(payload, line=line, column=column)
    url = _require_text(payload, "url", line=line, column=column)
    headers = _read_headers(payload, line=line, column=column)
    timeout_seconds = _read_timeout(payload, line=line, column=column)
    body = _read_body(payload, method=method, line=line, column=column)
    send_headers, trace_headers, secret_names = _resolve_headers(headers)
    if secret_names:
        _require_secrets_capability(ctx, line=line, column=column)
    obs = getattr(ctx, "observability", None)
    span_id = None
    if obs:
        span_id = obs.start_span(
            ctx,
            name=f"http:{tool.name}",
            kind="http",
            details={"tool": tool.name, "method": method},
            timing_name="capability",
            timing_labels={"capability": "http", "tool": tool.name},
        )
    span_status = "ok"
    try:
        trace_event = studio_effect_adapter.record_http_request(
            ctx,
            tool_name=tool.name,
            method=method,
            url=url,
            headers=trace_headers,
            body=body,
        )
        try:
            req = request.Request(url, method=method, headers=_header_dict(send_headers), data=None)
            with safe_urlopen(req, timeout_seconds) as resp:
                status = int(getattr(resp, "status", None) or resp.getcode())
                raw = resp.read()
                body_text = raw.decode("utf-8", errors="replace")
                response_headers = _sorted_headers(resp.headers.items())
        except Exception as err:
            span_status = "error"
            studio_effect_adapter.record_http_error(trace_event, message=str(err))
            raise
        output = _build_output(
            tool,
            status=status,
            headers=response_headers,
            body=body_text,
            line=line,
            column=column,
        )
        studio_effect_adapter.record_http_response(
            trace_event,
            status=status,
            headers=response_headers,
            body=body_text,
        )
        validate_tool_fields(
            fields=tool.output_fields,
            payload=output,
            tool_name=tool.name,
            phase="output",
            line=line,
            column=column,
            type_mode="tool",
            expect_object=True,
        )
        return output
    except Exception:
        span_status = "error"
        raise
    finally:
        if span_id:
            obs.end_span(ctx, span_id, status=span_status)


def safe_urlopen(req, timeout):
    return safe_urlopen_with_tls_fallback(req, timeout_seconds=timeout)


def _build_output(
    tool: ir.ToolDecl,
    *,
    status: int,
    headers: list[dict],
    body: str,
    line: int | None,
    column: int | None,
) -> dict:
    json_value = _parse_json(body)
    available: dict[str, object] = {
        "status": status,
        "headers": headers,
        "body": body,
    }
    if json_value is not None:
        available["json"] = json_value
    output: dict[str, object] = {}
    for field in tool.output_fields:
        if field.name not in ALLOWED_OUTPUT_FIELDS:
            raise Namel3ssError(
                _invalid_output_field_message(tool.name),
                line=line,
                column=column,
            )
        if field.name == "json" and json_value is None:
            raise Namel3ssError(
                build_guidance_message(
                    what=f'HTTP tool "{tool.name}" expected JSON output.',
                    why="The response body was not valid JSON.",
                    fix="Remove the json output field or return JSON from the endpoint.",
                    example='output:\n  status is number\n  body is text',
                ),
                line=line,
                column=column,
            )
        if field.name in available:
            output[field.name] = available[field.name]
    return output


def _validate_http_tool_schema(tool: ir.ToolDecl, *, line: int | None, column: int | None) -> None:
    input_fields = {field.name: field for field in tool.input_fields}
    output_fields = {field.name: field for field in tool.output_fields}
    _require_field(input_fields, "url", tool.name, line=line, column=column)
    _require_type(input_fields, "url", "text", tool.name, line=line, column=column)
    _require_type_optional(input_fields, "method", "text", tool.name, line=line, column=column)
    _require_type_optional(input_fields, "headers", "json", tool.name, line=line, column=column)
    _require_type_optional(input_fields, "body", "json", tool.name, line=line, column=column)
    _require_type_optional(input_fields, "timeout_seconds", "number", tool.name, line=line, column=column)
    for field in input_fields.values():
        if field.name not in ALLOWED_INPUT_FIELDS:
            raise Namel3ssError(
                _invalid_input_field_message(tool.name),
                line=line,
                column=column,
            )
    for field in output_fields.values():
        if field.name not in ALLOWED_OUTPUT_FIELDS:
            raise Namel3ssError(
                _invalid_output_field_message(tool.name),
                line=line,
                column=column,
            )
    _require_type_optional(output_fields, "status", "number", tool.name, line=line, column=column)
    _require_type_optional(output_fields, "headers", "json", tool.name, line=line, column=column)
    _require_type_optional(output_fields, "body", "text", tool.name, line=line, column=column)
    _require_type_optional(output_fields, "json", "json", tool.name, line=line, column=column)


def _read_method(payload: dict, *, line: int | None, column: int | None) -> str:
    value = payload.get("method")
    if value is None:
        return "GET"
    if not isinstance(value, str):
        raise Namel3ssError("HTTP method must be text", line=line, column=column)
    method = value.strip().upper()
    if method != "GET":
        raise Namel3ssError(
            build_guidance_message(
                what=f"HTTP method '{method}' is not supported yet.",
                why="Only GET requests are available in the built-in HTTP capability.",
                fix="Use GET or omit the method field.",
                example='method is "GET"',
            ),
            line=line,
            column=column,
        )
    return method


def _require_text(payload: dict, key: str, *, line: int | None, column: int | None) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise Namel3ssError(f"HTTP {key} must be a non-empty string", line=line, column=column)
    return value.strip()


def _read_headers(payload: dict, *, line: int | None, column: int | None) -> list[dict]:
    value = payload.get("headers", {})
    if value is None:
        return []
    if not isinstance(value, dict):
        raise Namel3ssError("HTTP headers must be an object", line=line, column=column)
    headers: list[dict] = []
    for key, raw in value.items():
        if not isinstance(key, str) or not isinstance(raw, str):
            raise Namel3ssError("HTTP headers must be string keys and values", line=line, column=column)
        header_name = key.strip()
        header_value = raw if isinstance(raw, SecretValue) else raw.strip()
        headers.append({"name": header_name, "value": header_value})
    return _sorted_headers(headers)


def _read_timeout(payload: dict, *, line: int | None, column: int | None) -> int:
    value = payload.get("timeout_seconds", 10)
    if isinstance(value, bool) or not is_number(value):
        raise Namel3ssError("timeout_seconds must be a number", line=line, column=column)
    seconds = int(value)
    if seconds <= 0:
        raise Namel3ssError("timeout_seconds must be positive", line=line, column=column)
    return seconds


def _read_body(payload: dict, *, method: str, line: int | None, column: int | None) -> object | None:
    if "body" not in payload:
        return None
    if method != "GET":
        raise Namel3ssError("HTTP body is not supported yet", line=line, column=column)
    raise Namel3ssError(
        build_guidance_message(
            what="HTTP body is not supported for GET requests.",
            why="The built-in HTTP capability is read-only.",
            fix="Remove the body field.",
            example='url is "https://example.com"',
        ),
        line=line,
        column=column,
    )


def _parse_json(body: str) -> object | None:
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return None


def _sorted_headers(items) -> list[dict]:
    headers: list[dict] = []
    for item in items:
        name = None
        value = None
        if isinstance(item, dict):
            name = item.get("name")
            value = item.get("value")
        else:
            try:
                name, value = item
            except (TypeError, ValueError):
                continue
        if not isinstance(name, str) or not isinstance(value, str):
            continue
        headers.append({"name": name, "value": value})
    headers.sort(key=lambda item: (item["name"].lower(), item["value"]))
    return headers


def _header_dict(headers: list[dict]) -> dict[str, str]:
    return {entry["name"]: entry["value"] for entry in headers}


def _resolve_headers(headers: list[dict]) -> tuple[list[dict], list[dict], set[str]]:
    send_headers: list[dict] = []
    trace_headers: list[dict] = []
    secret_names: set[str] = set()
    for header in headers:
        name = header.get("name") if isinstance(header, dict) else None
        value = header.get("value") if isinstance(header, dict) else None
        if not isinstance(name, str) or not isinstance(value, str):
            continue
        if isinstance(value, SecretValue):
            secret_names.update(value.secret_names)
            send_value = value.secret_value
            trace_value = str(value)
        else:
            send_value = value
            trace_value = value
        send_headers.append({"name": name, "value": send_value})
        trace_headers.append({"name": name, "value": trace_value})
    return send_headers, trace_headers, secret_names


def _require_secrets_capability(ctx, *, line: int | None, column: int | None) -> None:
    allowed = set(getattr(ctx, "capabilities", ()) or ())
    if "secrets" in allowed:
        return
    raise Namel3ssError(
        build_guidance_message(
            what="Secrets capability is not enabled.",
            why="Secrets are deny-by-default and must be explicitly allowed.",
            fix="Add 'secrets' to the capabilities block in app.ai.",
            example="capabilities:\n  secrets",
        ),
        line=line,
        column=column,
    )


def _require_field(fields: dict[str, ir.ToolField], name: str, tool_name: str, *, line: int | None, column: int | None) -> None:
    if name in fields:
        return
    raise Namel3ssError(
        build_guidance_message(
            what=f'HTTP tool "{tool_name}" is missing "{name}" input.',
            why="HTTP tools must declare a url field.",
            fix=f'Add `{name} is text` to the input block.',
            example='input:\n  url is text',
        ),
        line=line,
        column=column,
    )


def _require_type(
    fields: dict[str, ir.ToolField],
    name: str,
    expected: str,
    tool_name: str,
    *,
    line: int | None,
    column: int | None,
) -> None:
    field = fields.get(name)
    if not field:
        return
    if field.type_name != expected:
        raise Namel3ssError(
            build_guidance_message(
                what=f'HTTP tool "{tool_name}" input "{name}" must be {expected}.',
                why=f"The tool declares {name} as {field.type_name}.",
                fix=f"Update {name} to {expected}.",
                example=f'input:\n  {name} is {expected}',
            ),
            line=line,
            column=column,
        )


def _require_type_optional(
    fields: dict[str, ir.ToolField],
    name: str,
    expected: str,
    tool_name: str,
    *,
    line: int | None,
    column: int | None,
) -> None:
    if name not in fields:
        return
    _require_type(fields, name, expected, tool_name, line=line, column=column)


def _invalid_input_field_message(tool_name: str) -> str:
    return build_guidance_message(
        what=f'HTTP tool "{tool_name}" has unsupported input fields.',
        why="HTTP tools only support url, method, headers, body, and timeout_seconds.",
        fix="Remove unsupported input fields.",
        example='input:\n  url is text\n  method is optional text',
    )


def _invalid_output_field_message(tool_name: str) -> str:
    return build_guidance_message(
        what=f'HTTP tool "{tool_name}" has unsupported output fields.',
        why="HTTP tools only support status, headers, body, and json outputs.",
        fix="Remove unsupported output fields.",
        example='output:\n  status is number\n  body is text',
    )


__all__ = ["execute_http_tool"]
