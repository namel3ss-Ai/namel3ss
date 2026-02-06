from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class _Param:
    name: str
    location: str
    schema: dict
    required: bool


@dataclass(frozen=True)
class _Operation:
    name: str
    method: str
    path: str
    path_params: tuple[_Param, ...]
    query_params: tuple[_Param, ...]
    request_schema: dict | None
    response_schema: dict | None


def _collect_operations(spec: dict) -> list[_Operation]:
    operations: list[_Operation] = []
    paths = spec.get("paths") or {}
    for path in sorted(paths.keys()):
        methods = paths.get(path) or {}
        for method in sorted(methods.keys()):
            op = methods[method]
            op_id = str(op.get("operationId") or f"{method}_{path}")
            params = op.get("parameters") or []
            path_params: list[_Param] = []
            query_params: list[_Param] = []
            for param in params:
                if not isinstance(param, dict):
                    continue
                name = str(param.get("name") or "")
                location = str(param.get("in") or "")
                if not name or location not in {"path", "query"}:
                    continue
                schema = param.get("schema") if isinstance(param.get("schema"), dict) else {}
                required = bool(param.get("required"))
                entry = _Param(name=name, location=location, schema=schema, required=required)
                if location == "path":
                    path_params.append(entry)
                else:
                    query_params.append(entry)
            request_schema = _extract_request_schema(op)
            response_schema = _extract_response_schema(op)
            operations.append(
                _Operation(
                    name=op_id,
                    method=method,
                    path=path,
                    path_params=tuple(sorted(path_params, key=lambda item: item.name)),
                    query_params=tuple(sorted(query_params, key=lambda item: item.name)),
                    request_schema=request_schema,
                    response_schema=response_schema,
                )
            )
    operations.sort(key=lambda item: item.name)
    return operations


def _extract_request_schema(operation: dict) -> dict | None:
    request = operation.get("requestBody")
    if not isinstance(request, dict):
        return None
    content = request.get("content")
    if not isinstance(content, dict):
        return None
    json_payload = content.get("application/json")
    if not isinstance(json_payload, dict):
        return None
    schema = json_payload.get("schema")
    return schema if isinstance(schema, dict) else None


def _extract_response_schema(operation: dict) -> dict | None:
    responses = operation.get("responses")
    if not isinstance(responses, dict):
        return None
    response = responses.get("200") or responses.get("201")
    if not isinstance(response, dict):
        return None
    content = response.get("content")
    if not isinstance(content, dict):
        return None
    json_payload = content.get("application/json")
    if not isinstance(json_payload, dict):
        return None
    schema = json_payload.get("schema")
    return schema if isinstance(schema, dict) else None


def _collect_component_schemas(spec: dict) -> dict[str, dict]:
    components = spec.get("components") or {}
    schemas = components.get("schemas") if isinstance(components, dict) else {}
    if not isinstance(schemas, dict):
        return {}
    return {str(name): schema for name, schema in schemas.items() if isinstance(schema, dict)}


def _merge_types(base: dict[str, dict], extra: dict[str, dict]) -> dict[str, dict]:
    merged = dict(base)
    for name, schema in extra.items():
        if name not in merged:
            merged[name] = schema
    return merged


def _schema_ref_name(schema: dict | None) -> str | None:
    if not isinstance(schema, dict):
        return None
    ref = schema.get("$ref")
    if isinstance(ref, str) and ref:
        return ref.split("/")[-1]
    return None


def _schema_is_object(schema: dict | None) -> bool:
    if not isinstance(schema, dict):
        return False
    if schema.get("type") != "object":
        return False
    return isinstance(schema.get("properties"), dict)


def _pascal_case(value: str) -> str:
    parts = re.split(r"[^0-9A-Za-z]+", value)
    parts = [part for part in parts if part]
    if not parts:
        return "Call"
    return "".join(part.capitalize() for part in parts)


def _ensure_operation_types(op: _Operation, extra: dict[str, dict], components: dict[str, dict]) -> None:
    if op.path_params or op.query_params:
        name = f"{_pascal_case(op.name)}Params"
        if name not in components and name not in extra:
            extra[name] = _params_schema(op.path_params + op.query_params)
    if op.request_schema and _schema_ref_name(op.request_schema) is None and _schema_is_object(op.request_schema):
        name = f"{_pascal_case(op.name)}Request"
        if name not in components and name not in extra:
            extra[name] = op.request_schema
    if op.response_schema and _schema_ref_name(op.response_schema) is None and _schema_is_object(op.response_schema):
        name = f"{_pascal_case(op.name)}Response"
        if name not in components and name not in extra:
            extra[name] = op.response_schema


def _params_schema(params: tuple[_Param, ...]) -> dict:
    properties: dict[str, dict] = {}
    required: list[str] = []
    for param in params:
        properties[param.name] = param.schema
        if param.required:
            required.append(param.name)
    schema = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema


def _resolve_base_url(spec: dict) -> str:
    servers = spec.get("servers")
    if isinstance(servers, list) and servers:
        first = servers[0]
        if isinstance(first, dict):
            url = first.get("url")
            if isinstance(url, str) and url:
                return url
    return "http://127.0.0.1:7340"


def _snake_case(value: str) -> str:
    cleaned = re.sub(r"[^0-9A-Za-z_]+", "_", value)
    cleaned = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", cleaned)
    return cleaned.strip("_").lower() or "call"


def _camel_case(value: str) -> str:
    parts = re.split(r"[^0-9A-Za-z]+", value)
    parts = [part for part in parts if part]
    if not parts:
        return "call"
    first = parts[0].lower()
    rest = "".join(part.capitalize() for part in parts[1:])
    return first + rest


__all__ = [
    "_Param",
    "_Operation",
    "_collect_operations",
    "_extract_request_schema",
    "_extract_response_schema",
    "_collect_component_schemas",
    "_merge_types",
    "_schema_ref_name",
    "_schema_is_object",
    "_pascal_case",
    "_ensure_operation_types",
    "_params_schema",
    "_resolve_base_url",
    "_snake_case",
    "_camel_case",
]
