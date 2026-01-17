from __future__ import annotations

from namel3ss.observe import summarize_value
from namel3ss.secrets import collect_secret_values, redact_text


def record_http_request(
    ctx,
    *,
    tool_name: str,
    method: str,
    url: str,
    headers: list[dict],
    body: object | None,
) -> dict:
    secret_values = collect_secret_values(ctx.config)
    event = {
        "type": "tool_call",
        "tool": tool_name,
        "tool_name": tool_name,
        "kind": "http",
        "title": f"HTTP {method.upper()}",
        "input": {
            "method": method.upper(),
            "url": url,
            "headers": _redact_headers(headers, secret_values),
            "body": summarize_value(body, secret_values=secret_values),
        },
    }
    target = _trace_target(ctx)
    target.append(event)
    return target[-1] if target else event


def record_http_response(event: dict, *, status: int, headers: list[dict], body: object) -> None:
    event["output"] = {
        "status": status,
        "headers": headers,
        "body": summarize_value(body),
    }


def record_http_error(event: dict, *, message: str) -> None:
    event["error"] = message


def record_file_operation(
    ctx,
    *,
    tool_name: str,
    operation: str,
    path: str,
    content: object | None = None,
) -> dict:
    secret_values = collect_secret_values(ctx.config)
    event = {
        "type": "tool_call",
        "tool": tool_name,
        "tool_name": tool_name,
        "kind": "file",
        "title": f"File {operation}",
        "input": {
            "operation": operation,
            "path": path,
        },
    }
    if content is not None:
        event["input"]["content"] = summarize_value(content, secret_values=secret_values)
    target = _trace_target(ctx)
    target.append(event)
    return target[-1] if target else event


def record_file_result(event: dict, *, content: object | None = None, ok: bool | None = None) -> None:
    output: dict[str, object] = {}
    if ok is not None:
        output["ok"] = ok
    if content is not None:
        output["content"] = summarize_value(content)
    if output:
        event["output"] = output


def record_file_error(event: dict, *, message: str) -> None:
    event["error"] = message


def record_job_enqueued(ctx, *, job_name: str, payload: object) -> None:
    event = {
        "type": "job_enqueued",
        "title": f"Job enqueued: {job_name}",
        "job": job_name,
        "input": summarize_value(payload),
    }
    ctx.traces.append(event)


def record_job_started(ctx, *, job_name: str, payload: object) -> None:
    event = {
        "type": "job_started",
        "title": f"Job started: {job_name}",
        "job": job_name,
        "input": summarize_value(payload),
    }
    ctx.traces.append(event)


def record_job_finished(ctx, *, job_name: str, output: object | None, status: str) -> None:
    event = {
        "type": "job_finished",
        "title": f"Job finished: {job_name}",
        "job": job_name,
        "status": status,
    }
    if output is not None:
        event["output"] = summarize_value(output)
    ctx.traces.append(event)


def _redact_headers(headers: list[dict], secret_values: list[str]) -> list[dict]:
    redacted: list[dict] = []
    for header in headers:
        name = header.get("name")
        value = header.get("value")
        if not isinstance(name, str) or not isinstance(value, str):
            continue
        redacted.append({"name": name, "value": redact_text(value, secret_values)})
    return redacted


def _trace_target(ctx) -> list:
    return ctx.pending_tool_traces if getattr(ctx, "tool_call_source", None) == "ai" else ctx.traces


__all__ = [
    "record_file_error",
    "record_file_operation",
    "record_file_result",
    "record_http_error",
    "record_http_request",
    "record_http_response",
    "record_job_enqueued",
    "record_job_finished",
    "record_job_started",
]
