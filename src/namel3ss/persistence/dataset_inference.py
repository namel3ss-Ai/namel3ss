from __future__ import annotations

import csv
import json
from io import StringIO


def infer_dataset_schema(
    *,
    filename: str | None,
    content_type: str | None,
    data: bytes,
) -> dict | None:
    kind = _detect_kind(filename, content_type)
    if kind == "csv":
        return _infer_csv_schema(data)
    if kind == "json":
        return _infer_json_schema(data)
    return None


def _detect_kind(filename: str | None, content_type: str | None) -> str:
    content = (content_type or "").split(";", 1)[0].strip().lower()
    name = (filename or "").lower()
    if content in {"text/csv", "application/csv"} or name.endswith(".csv"):
        return "csv"
    if content in {"application/json", "text/json"} or name.endswith(".json"):
        return "json"
    return ""


def _infer_csv_schema(data: bytes) -> dict | None:
    try:
        text = data.decode("utf-8")
    except Exception:
        return None
    reader = csv.DictReader(StringIO(text))
    headers = reader.fieldnames or []
    if not headers:
        return None
    samples: list[dict[str, str]] = []
    for idx, row in enumerate(reader):
        if not isinstance(row, dict):
            continue
        samples.append({key: str(row.get(key, "") or "") for key in headers})
        if idx >= 49:
            break
    schema: dict[str, str] = {}
    for header in headers:
        values = [row.get(header, "") for row in samples if isinstance(row, dict)]
        schema[header] = _infer_scalar_type(values)
    return _sorted_schema(schema)


def _infer_json_schema(data: bytes) -> dict | None:
    try:
        payload = json.loads(data.decode("utf-8"))
    except Exception:
        return None
    if isinstance(payload, list):
        items = [item for item in payload if isinstance(item, dict)]
        if not items:
            return None
        return _schema_from_objects(items)
    if isinstance(payload, dict):
        return _schema_from_objects([payload])
    return None


def _schema_from_objects(items: list[dict]) -> dict | None:
    keys = set()
    for item in items:
        keys.update(item.keys())
    if not keys:
        return None
    schema: dict[str, str] = {}
    for key in sorted(keys):
        values = [item.get(key) for item in items]
        schema[key] = _infer_value_type(values)
    return _sorted_schema(schema)


def _infer_scalar_type(values: list[str]) -> str:
    if not values:
        return "text"
    if all(_looks_like_number(value) for value in values if value != ""):
        return "number"
    if all(_looks_like_boolean(value) for value in values if value != ""):
        return "boolean"
    return "text"


def _infer_value_type(values: list[object]) -> str:
    normalized = [value for value in values if value is not None]
    if not normalized:
        return "text"
    if all(isinstance(value, bool) for value in normalized):
        return "boolean"
    if all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in normalized):
        return "number"
    if all(isinstance(value, str) for value in normalized):
        return _infer_scalar_type([value for value in normalized if isinstance(value, str)])
    return "text"


def _looks_like_number(value: str) -> bool:
    try:
        float(value)
        return True
    except Exception:
        return False


def _looks_like_boolean(value: str) -> bool:
    return value.strip().lower() in {"true", "false", "yes", "no", "1", "0"}


def _sorted_schema(schema: dict[str, str]) -> dict[str, str]:
    return {key: schema[key] for key in sorted(schema.keys())}


__all__ = ["infer_dataset_schema"]
