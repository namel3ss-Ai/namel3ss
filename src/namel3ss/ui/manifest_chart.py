from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir
from namel3ss.runtime.records.service import build_record_scope
from namel3ss.schema import records as schema
from namel3ss.ui.manifest.state_defaults import StateContext
from namel3ss.validation import ValidationMode, add_warning

_ALLOWED_TYPES = {"bar", "line", "summary"}


def _build_chart_element(
    item: ir.ChartItem,
    record_map: dict[str, schema.RecordSchema],
    *,
    page_name: str,
    page_slug: str,
    element_id: str,
    index: int,
    identity: dict | None,
    state_ctx: StateContext,
    mode: ValidationMode,
    warnings: list | None,
    store,
) -> dict:
    chart_type = (item.chart_type or "summary").lower()
    if chart_type not in _ALLOWED_TYPES:
        raise Namel3ssError(
            f"Chart type '{chart_type}' is not supported",
            line=item.line,
            column=item.column,
        )
    record = None
    rows: list[dict] = []
    source_label = None
    if item.record_name:
        record = record_map.get(item.record_name)
        if record is None:
            raise Namel3ssError(
                f"Chart references unknown record '{item.record_name}'",
                line=item.line,
                column=item.column,
            )
        if store is not None:
            scope = build_record_scope(record, identity)
            rows = store.list_records(record, scope=scope)[:50]
        source_label = record.name
    elif item.source:
        source_label = _state_path_label(item.source)
        rows = _resolve_state_list(item.source, state_ctx, mode, warnings, item.line, item.column)
    x, y = _resolve_mapping(chart_type, item, record, rows)
    explain = item.explain or _auto_explain(chart_type, source_label or "data", x, y)

    element = {
        "type": "chart",
        "chart_type": chart_type,
        "element_id": element_id,
        "page": page_name,
        "page_slug": page_slug,
        "index": index,
        "line": item.line,
        "column": item.column,
        "explain": explain,
    }
    if item.record_name:
        element["record"] = item.record_name
    if item.source:
        element["source"] = source_label
    if x is not None:
        element["x"] = x
    if y is not None:
        element["y"] = y

    if chart_type == "summary":
        element["summary"] = _build_summary(rows, y, item.line, item.column)
        return element

    series = _build_series(rows, x, y, item.line, item.column)
    element["series"] = series
    return element


def _resolve_mapping(
    chart_type: str,
    item: ir.ChartItem,
    record: schema.RecordSchema | None,
    rows: list[dict],
) -> tuple[str | None, str | None]:
    x = item.x
    y = item.y
    if record is not None:
        if y is None:
            y = _default_numeric_field(record)
        if x is None and chart_type in {"bar", "line"}:
            x = _default_category_field(record)
    else:
        if y is None:
            y = _default_numeric_key(rows)
        if x is None and chart_type in {"bar", "line"}:
            x = _default_category_key(rows)
    if chart_type in {"bar", "line"}:
        if x is None or y is None:
            raise Namel3ssError("Chart requires x and y mappings", line=item.line, column=item.column)
    return x, y


def _default_numeric_field(record: schema.RecordSchema) -> str | None:
    for field in record.fields:
        if _is_numeric_type(field.type_name):
            return field.name
    return None


def _default_category_field(record: schema.RecordSchema) -> str | None:
    for field in record.fields:
        if _is_category_type(field.type_name):
            return field.name
    return None


def _default_numeric_key(rows: list[dict]) -> str | None:
    keys = _sorted_keys(rows)
    for key in keys:
        if _column_is_numeric(rows, key):
            return key
    return None


def _default_category_key(rows: list[dict]) -> str | None:
    keys = _sorted_keys(rows)
    for key in keys:
        if _column_is_category(rows, key):
            return key
    return None


def _sorted_keys(rows: list[dict]) -> list[str]:
    keys: set[str] = set()
    for row in rows:
        if isinstance(row, dict):
            keys.update(str(k) for k in row.keys())
    return sorted(keys)


def _column_is_numeric(rows: list[dict], key: str) -> bool:
    seen = False
    for row in rows:
        if not isinstance(row, dict):
            return False
        if key not in row:
            continue
        value = row.get(key)
        if value is None:
            continue
        if not _is_number(value):
            return False
        seen = True
    return seen


def _column_is_category(rows: list[dict], key: str) -> bool:
    seen = False
    for row in rows:
        if not isinstance(row, dict):
            return False
        if key not in row:
            continue
        value = row.get(key)
        if value is None:
            continue
        if not _is_category(value):
            return False
        seen = True
    return seen


def _build_series(rows: list[dict], x: str, y: str, line: int | None, column: int | None) -> list[dict]:
    series: list[dict] = []
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            raise Namel3ssError(f"Row {idx} must be an object", line=line, column=column)
        if x not in row or y not in row:
            raise Namel3ssError(f"Row {idx} is missing chart fields", line=line, column=column)
        x_val = row.get(x)
        y_val = row.get(y)
        if not _is_category(x_val):
            raise Namel3ssError(f"Row {idx} has invalid x value", line=line, column=column)
        if not _is_number(y_val):
            raise Namel3ssError(f"Row {idx} has invalid y value", line=line, column=column)
        series.append({"x": x_val, "y": y_val})
    return series


def _build_summary(rows: list[dict], y: str | None, line: int | None, column: int | None) -> dict:
    summary = {"count": len(rows)}
    if y is None:
        return summary
    total = 0
    count = 0
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            raise Namel3ssError(f"Row {idx} must be an object", line=line, column=column)
        value = row.get(y)
        if value is None:
            continue
        if not _is_number(value):
            raise Namel3ssError(f"Row {idx} has invalid y value", line=line, column=column)
        total += value
        count += 1
    summary["total"] = total
    if count:
        summary["average"] = total / count
    return summary


def _state_path_label(path: ir.StatePath) -> str:
    return f"state.{'.'.join(path.path)}"


def _resolve_state_list(
    source: ir.StatePath,
    state_ctx: StateContext,
    mode: ValidationMode,
    warnings: list | None,
    line: int | None,
    column: int | None,
) -> list[dict]:
    path = source.path
    value, _ = state_ctx.value(path, default=[], register_default=False)
    if mode == ValidationMode.STATIC and not state_ctx.declared(path) and state_ctx.defaults.warn_once(path):
        add_warning(
            warnings,
            code="state.default.missing",
            message=f"State path 'state.{'.'.join(path)}' is not declared; using empty list during static validation.",
            fix=f"Declare a default for state.{'.'.join(path)} to silence this warning.",
            path=path,
            line=line,
            column=column,
            enforced_at="runtime",
        )
    if not isinstance(value, list):
        raise Namel3ssError("Chart source must be a list", line=line, column=column)
    for idx, entry in enumerate(value):
        if not isinstance(entry, dict):
            raise Namel3ssError(f"Row {idx} must be an object", line=line, column=column)
    return value


def _auto_explain(chart_type: str, source: str, x: str | None, y: str | None) -> str:
    if chart_type == "summary":
        if y:
            return f"Summary of {source} for {y}."
        return f"Summary of {source}."
    if x and y:
        label = "Bar" if chart_type == "bar" else "Line"
        return f"{label} chart of {y} by {x} for {source}."
    return f"Chart of {source}."


def _is_category(value: object) -> bool:
    return isinstance(value, (str, int, float)) and not isinstance(value, bool)


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_numeric_type(type_name: str) -> bool:
    return type_name in {"number", "int", "integer"}


def _is_category_type(type_name: str) -> bool:
    return type_name in {"text", "string", "str", "number", "int", "integer"}


__all__ = ["_build_chart_element", "_state_path_label"]
