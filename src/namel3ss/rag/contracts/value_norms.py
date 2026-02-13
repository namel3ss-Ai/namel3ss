from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def map_value(value: object) -> dict[str, object]:
    if not isinstance(value, Mapping):
        return {}
    return {str(key): value[key] for key in sorted(value.keys(), key=lambda item: str(item))}


def text_value(value: object, *, default: str = "") -> str:
    if isinstance(value, str):
        return value.strip()
    return default


def int_value(value: object, *, default: int = 0, minimum: int | None = None) -> int:
    if isinstance(value, bool):
        output = default
    else:
        try:
            output = int(value)
        except Exception:
            output = default
    if minimum is not None and output < minimum:
        return minimum
    return output


def float_value(value: object, *, default: float = 0.0, precision: int = 6) -> float:
    if isinstance(value, bool):
        number = Decimal(str(default))
    else:
        try:
            number = Decimal(str(value))
        except (InvalidOperation, ValueError):
            number = Decimal(str(default))
    places = max(0, int(precision))
    quant = Decimal("1") if places == 0 else Decimal("1").scaleb(-places)
    return float(number.quantize(quant, rounding=ROUND_HALF_UP))


def string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    seen: set[str] = set()
    rows: list[str] = []
    for item in value:
        text = text_value(item)
        if not text or text in seen:
            continue
        seen.add(text)
        rows.append(text)
    return rows


def sorted_string_list(value: object) -> list[str]:
    return sorted(string_list(value))


def normalize_span(value: object) -> dict[str, int]:
    data = map_value(value)
    start_char = int_value(data.get("start_char"), default=0, minimum=0)
    end_char = int_value(data.get("end_char"), default=start_char, minimum=start_char)
    return {
        "end_char": end_char,
        "start_char": start_char,
    }


def normalize_bbox(value: object) -> list[float]:
    if not isinstance(value, list):
        return []
    if len(value) != 4:
        return []
    return [float_value(item, default=0.0, precision=6) for item in value]


def normalize_token_positions(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    rows: list[dict[str, object]] = []
    for index, item in enumerate(value):
        data = map_value(item)
        token = text_value(data.get("token"))
        start_char = int_value(data.get("start_char"), default=0, minimum=0)
        end_char = int_value(data.get("end_char"), default=start_char, minimum=start_char)
        row: dict[str, object] = {
            "end_char": end_char,
            "index": int_value(data.get("index"), default=index, minimum=0),
            "start_char": start_char,
            "token": token,
        }
        bbox = normalize_bbox(data.get("bbox"))
        if bbox:
            row["bbox"] = bbox
        rows.append(row)
    rows.sort(key=lambda item: (int(item.get("index") or 0), int(item.get("start_char") or 0), int(item.get("end_char") or 0), str(item.get("token") or "")))
    return rows


def merge_extensions(*payloads: object) -> dict[str, object]:
    merged: dict[str, object] = {}
    for payload in payloads:
        data = map_value(payload)
        for key in data.keys():
            merged[key] = data[key]
    return {key: merged[key] for key in sorted(merged.keys())}


def unknown_extensions(value: object, *, known_keys: set[str]) -> dict[str, object]:
    data = map_value(value)
    output: dict[str, object] = {}
    for key in data.keys():
        if key in known_keys:
            continue
        output[key] = data[key]
    return output


__all__ = [
    "float_value",
    "int_value",
    "map_value",
    "merge_extensions",
    "normalize_bbox",
    "normalize_span",
    "normalize_token_positions",
    "sorted_string_list",
    "string_list",
    "text_value",
    "unknown_extensions",
]
