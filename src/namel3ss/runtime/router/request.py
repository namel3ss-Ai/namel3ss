from __future__ import annotations

import json

from namel3ss.errors.base import Namel3ssError


def query_params(query: dict[str, list[str]]) -> dict[str, str]:
    params: dict[str, str] = {}
    for key, values in query.items():
        if not values:
            continue
        params[key] = values[0]
    return params


def coerce_params(values: dict[str, str], fields: dict[str, object]) -> dict[str, object]:
    coerced: dict[str, object] = {}
    for key, raw in values.items():
        field = fields.get(key)
        type_name = getattr(field, "type_name", None) if field else None
        coerced[key] = coerce_value(raw, type_name)
    return coerced


def coerce_value(value: str, type_name: str | None) -> object:
    if not type_name:
        return value
    normalized = type_name.strip().lower()
    if normalized.startswith("list<") and normalized.endswith(">"):
        inner = normalized[5:-1].strip()
        parts = [part for part in value.split(",") if part != ""]
        return [coerce_value(part.strip(), inner) for part in parts]
    if normalized == "number":
        try:
            return int(value)
        except Exception:
            try:
                return float(value)
            except Exception:
                return value
    if normalized == "boolean":
        lowered = value.strip().lower()
        if lowered in {"true", "yes", "1"}:
            return True
        if lowered in {"false", "no", "0"}:
            return False
    return value


def read_json_body(headers: dict[str, str], rfile) -> dict[str, object]:
    length_header = headers.get("Content-Length") or headers.get("content-length")
    if not length_header:
        return {}
    try:
        length = int(length_header)
    except ValueError:
        return {}
    raw = rfile.read(length) if length else b""
    if not raw:
        return {}
    try:
        decoded = raw.decode("utf-8")
        payload = json.loads(decoded or "{}")
    except Exception:
        raise Namel3ssError("Request body must be valid JSON.")
    if not isinstance(payload, dict):
        raise Namel3ssError("Request body must be a JSON object.")
    return payload


__all__ = ["coerce_params", "coerce_value", "query_params", "read_json_body"]
