from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.conventions.config import load_conventions_config
from namel3ss.runtime.conventions.formats import load_formats_config


_OPENAPI_VERSION = "3.0.3"
_PAGINATION_HINTS = {
    "page": "Page number, starting at 1.",
    "page_size": "Number of items per page.",
    "per_page": "Number of items per page.",
    "limit": "Maximum number of items to return.",
    "offset": "Number of items to skip.",
}
_FILTER_HINTS = {
    "filter": "Filter expression for narrowing results.",
    "search": "Search term to filter results.",
    "q": "Search term to filter results.",
}


@dataclass(frozen=True)
class _AIFlowSummary:
    name: str
    kind: str
    model: str
    prompt: str
    output_type: str


def build_openapi_spec(program) -> dict:
    info = {
        "title": _resolve_title(program),
        "version": _resolve_version(program),
    }
    components = {"schemas": {}}
    record_map = _record_map(program)
    _add_record_schemas(components["schemas"], record_map)
    _add_error_schemas(components["schemas"])
    _add_ai_flow_schemas(components["schemas"])
    ai_summaries = _collect_ai_summaries(program)
    conventions = load_conventions_config(getattr(program, "project_root", None), getattr(program, "app_path", None))
    formats = load_formats_config(getattr(program, "project_root", None), getattr(program, "app_path", None))
    paths = _build_paths(program, record_map, ai_summaries, conventions, formats)
    spec = {
        "openapi": _OPENAPI_VERSION,
        "info": info,
        "paths": paths,
        "components": components,
    }
    if ai_summaries:
        spec["x-ai-flows"] = [summary.__dict__ for summary in sorted(ai_summaries.values(), key=lambda item: item.name)]
    return spec


def _resolve_title(program) -> str:
    app_path = getattr(program, "app_path", None)
    if app_path:
        try:
            return Path(app_path).stem
        except Exception:
            return str(app_path)
    root = getattr(program, "project_root", None)
    if root:
        try:
            return Path(root).name
        except Exception:
            return str(root)
    return "namel3ss app"


def _resolve_version(program) -> str:
    version = getattr(program, "spec_version", None)
    return str(version) if version else "1.0.0"


def _record_map(program) -> dict[str, object]:
    records = getattr(program, "records", []) or []
    return {record.name: record for record in records}


def _build_paths(
    program,
    record_map: dict[str, object],
    ai_summaries: dict[str, _AIFlowSummary],
    conventions,
    formats,
) -> dict:
    paths: dict[str, dict] = {}
    routes = sorted(getattr(program, "routes", []) or [], key=_route_sort_key)
    for route in routes:
        if not getattr(route, "response", None):
            raise Namel3ssError(f'Route "{route.name}" is missing a response schema.')
        path_item = paths.setdefault(route.path, {})
        operation = _build_operation(route, record_map, ai_summaries, conventions, formats)
        path_item[route.method.lower()] = operation
    return paths


def _route_sort_key(route) -> tuple:
    return (route.path, route.method, route.name)


def _build_operation(route, record_map: dict[str, object], ai_summaries: dict[str, _AIFlowSummary], conventions, formats) -> dict:
    path_params = _path_params(route.path)
    route_conventions = conventions.for_route(route.name)
    allowed_formats = formats.formats_for_route(route.name)
    parameters = _build_parameters(route, record_map, path_params, route_conventions, allowed_formats)
    responses = _build_responses(route, record_map)
    operation: dict[str, object] = {
        "operationId": route.name,
        "summary": route.name,
        "parameters": parameters,
        "responses": responses,
        "x-flow": route.flow_name,
        "x-generated": bool(getattr(route, "generated", False)),
        "x-response-formats": list(allowed_formats),
    }
    if route.request:
        operation["requestBody"] = {
            "required": True,
            "content": {"application/json": {"schema": _field_map_schema(route.request, record_map)}},
        }
    summary = ai_summaries.get(route.flow_name)
    if summary:
        operation["description"] = _ai_description(summary)
        operation["x-ai"] = summary.__dict__
    return operation


def _build_parameters(route, record_map: dict[str, object], path_params: set[str], route_conventions, allowed_formats: tuple[str, ...]) -> list[dict]:
    parameters = []
    for name in sorted(route.parameters.keys()) if route.parameters else []:
        field = route.parameters[name]
        schema = _type_schema(field.type_name, record_map)
        location = "path" if name in path_params else "query"
        param = {
            "name": name,
            "in": location,
            "required": location == "path",
            "schema": schema,
        }
        hint = _param_hint(name)
        if hint:
            param["description"] = hint
        parameters.append(param)
    for name in sorted(path_params - set(route.parameters.keys() if route.parameters else [])):
        parameters.append(
            {
                "name": name,
                "in": "path",
                "required": True,
                "schema": {"type": "string"},
            }
        )
    list_fields = _list_response_fields(route)
    if list_fields:
        parameters.append(
            {
                "name": "page",
                "in": "query",
                "required": False,
                "schema": {"type": "number"},
                "description": _PAGINATION_HINTS["page"],
            }
        )
        parameters.append(
            {
                "name": "page_size",
                "in": "query",
                "required": False,
                "schema": {"type": "number"},
                "description": _PAGINATION_HINTS["page_size"],
            }
        )
        filter_desc = _FILTER_HINTS["filter"]
        if route_conventions.filter_fields:
            filter_desc = f"{filter_desc} Allowed fields: {', '.join(route_conventions.filter_fields)}."
        parameters.append(
            {
                "name": "filter",
                "in": "query",
                "required": False,
                "schema": {"type": "string"},
                "description": filter_desc,
            }
        )
    if allowed_formats and "toon" in allowed_formats:
        parameters.append(
            {
                "name": "format",
                "in": "query",
                "required": False,
                "schema": {"type": "string"},
                "description": "Response format. Allowed: " + ", ".join(sorted(set(allowed_formats))),
            }
        )
    return parameters


def _param_hint(name: str) -> str | None:
    key = name.lower()
    if key in _PAGINATION_HINTS:
        return _PAGINATION_HINTS[key]
    if key in _FILTER_HINTS:
        return _FILTER_HINTS[key]
    return None


def _build_responses(route, record_map: dict[str, object]) -> dict:
    responses = {
        "200": {
            "description": "Success.",
            "content": {"application/json": {"schema": _field_map_schema(route.response, record_map)}},
        },
        "400": {
            "description": "Bad request.",
            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorEnvelope"}}},
        },
        "500": {
            "description": "Internal error.",
            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorEnvelope"}}},
        },
    }
    return responses


def _field_map_schema(field_map: dict[str, object], record_map: dict[str, object]) -> dict:
    properties: dict[str, dict] = {}
    required: list[str] = []
    for name in sorted(field_map.keys()):
        field = field_map[name]
        properties[name] = _type_schema(getattr(field, "type_name", "text"), record_map)
        required.append(name)
    schema = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema


def _type_schema(type_name: str, record_map: dict[str, object]) -> dict:
    inner = _split_list_type(type_name)
    if inner:
        return {"type": "array", "items": _type_schema(inner, record_map)}
    normalized = type_name
    if normalized in {"text", "string", "str"}:
        return {"type": "string"}
    if normalized in {"number", "int", "integer"}:
        return {"type": "number"}
    if normalized in {"boolean", "bool"}:
        return {"type": "boolean"}
    if normalized == "json":
        return {"type": "object"}
    if normalized == "map":
        return {"type": "object", "additionalProperties": True}
    if normalized in record_map:
        return {"$ref": f"#/components/schemas/{normalized}"}
    raise Namel3ssError(f"OpenAPI: unknown type '{type_name}'.")


def _split_list_type(type_name: str) -> str | None:
    if not type_name.startswith("list<"):
        return None
    depth = 0
    start = None
    end = None
    for idx, ch in enumerate(type_name):
        if ch == "<":
            depth += 1
            if depth == 1:
                start = idx + 1
        elif ch == ">":
            depth -= 1
            if depth == 0:
                end = idx
                break
    if start is None or end is None or end != len(type_name) - 1:
        return None
    inner = type_name[start:end].strip()
    return inner or None


def _path_params(path: str) -> set[str]:
    return set(re.findall(r"\{([A-Za-z0-9_]+)\}", path))


def _add_record_schemas(target: dict[str, dict], record_map: dict[str, object]) -> None:
    for name in sorted(record_map.keys()):
        record = record_map[name]
        fields = getattr(record, "fields", []) or []
        properties: dict[str, dict] = {}
        required: list[str] = []
        for field in fields:
            properties[field.name] = _type_schema(field.type_name, record_map)
            required.append(field.name)
        schema = {"type": "object", "properties": properties}
        if required:
            schema["required"] = required
        target[name] = schema


def _add_error_schemas(target: dict[str, dict]) -> None:
    target["ErrorEnvelope"] = {
        "type": "object",
        "properties": {
            "code": {"type": "string"},
            "message": {"type": "string"},
            "remediation": {"type": "string"},
        },
        "required": ["code", "message", "remediation"],
    }


def _add_ai_flow_schemas(target: dict[str, dict]) -> None:
    target["LLMCall"] = _ai_schema_base("LLM call metadata.")
    target["Summarise"] = _ai_schema_base("Summarise metadata.")
    target["Translate"] = {
        "type": "object",
        "description": "Translate metadata.",
        "properties": {
            "model": {"type": "string"},
            "prompt": {"type": "string"},
            "dataset": {"type": "string"},
            "output_type": {"type": "string"},
            "source_language": {"type": "string"},
            "target_language": {"type": "string"},
        },
        "required": ["model", "source_language", "target_language"],
    }
    target["QA"] = {
        "type": "object",
        "description": "Question answering metadata.",
        "properties": {
            "model": {"type": "string"},
            "prompt": {"type": "string"},
            "dataset": {"type": "string"},
            "output_fields": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["model", "output_fields"],
    }
    target["COT"] = {
        "type": "object",
        "description": "Chain of thought metadata.",
        "properties": {
            "model": {"type": "string"},
            "prompt": {"type": "string"},
            "dataset": {"type": "string"},
            "output_fields": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["model", "output_fields"],
    }
    target["Chain"] = {
        "type": "object",
        "description": "Composable AI chain metadata.",
        "properties": {
            "steps": {"type": "array", "items": {"type": "object"}},
            "output_fields": {"type": "array", "items": {"type": "string"}},
            "tests": {"type": "object"},
        },
        "required": ["steps", "output_fields"],
    }
    target["RAG"] = {
        "type": "object",
        "description": "RAG metadata.",
        "properties": {
            "model": {"type": "string"},
            "prompt": {"type": "string"},
            "dataset": {"type": "string"},
            "output_type": {"type": "string"},
            "sources": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["model", "prompt", "sources"],
    }
    target["Classification"] = {
        "type": "object",
        "description": "Classification metadata.",
        "properties": {
            "model": {"type": "string"},
            "prompt": {"type": "string"},
            "dataset": {"type": "string"},
            "output_type": {"type": "string"},
            "labels": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["model", "prompt", "labels"],
    }


def _ai_schema_base(description: str) -> dict:
    return {
        "type": "object",
        "description": description,
        "properties": {
            "model": {"type": "string"},
            "prompt": {"type": "string"},
            "dataset": {"type": "string"},
            "output_type": {"type": "string"},
        },
        "required": ["model", "prompt"],
    }


def _collect_ai_summaries(program) -> dict[str, _AIFlowSummary]:
    summaries: dict[str, _AIFlowSummary] = {}
    for flow in getattr(program, "flows", []) or []:
        meta = getattr(flow, "ai_metadata", None)
        if meta is None:
            continue
        kind = getattr(meta, "kind", None) or "llm_call"
        output_type = getattr(meta, "output_type", None) or "text"
        summaries[flow.name] = _AIFlowSummary(
            name=flow.name,
            kind=kind,
            model=meta.model or "n/a",
            prompt=meta.prompt or "[dynamic prompt]",
            output_type=output_type,
        )
    for flow in getattr(program, "ai_flows", []) or []:
        output_type = flow.output_type or "text"
        summaries[flow.name] = _AIFlowSummary(
            name=flow.name,
            kind=flow.kind,
            model=flow.model or "n/a",
            prompt=flow.prompt or "[dynamic prompt]",
            output_type=output_type,
        )
    return summaries


def _list_response_fields(route) -> tuple[str, ...]:
    fields = getattr(route, "response", None) or {}
    names: list[str] = []
    for name, field in fields.items():
        type_name = getattr(field, "type_name", "")
        if isinstance(type_name, str) and type_name.startswith("list<"):
            names.append(name)
    return tuple(sorted(names))


def _ai_description(summary: _AIFlowSummary) -> str:
    return (
        f'AI flow type {summary.kind}. '
        f'Model is "{summary.model}". '
        f'Prompt is "{summary.prompt}". '
        f'Output is {summary.output_type}.'
    )


__all__ = ["build_openapi_spec"]
