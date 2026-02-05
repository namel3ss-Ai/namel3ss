from __future__ import annotations

from typing import Any


def parse_yaml(text: str) -> object:
    lines = _yaml_lines(text)
    if not lines:
        return {}
    data, index = _parse_yaml_block(lines, 0, 0)
    if index != len(lines):
        raise ValueError("YAML could not be parsed.")
    return data


def render_yaml(value: object) -> str:
    lines = _render_yaml(value, indent=0)
    return "\n".join(lines).rstrip() + "\n"


def _yaml_lines(text: str) -> list[tuple[int, str]]:
    lines: list[tuple[int, str]] = []
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        lines.append((indent, stripped))
    return lines


def _parse_yaml_block(lines: list[tuple[int, str]], index: int, indent: int) -> tuple[Any, int]:
    if index >= len(lines):
        return {}, index
    current_indent, current_line = lines[index]
    if current_line.startswith("- "):
        return _parse_yaml_list(lines, index, indent)
    return _parse_yaml_map(lines, index, indent)


def _parse_yaml_map(lines: list[tuple[int, str]], index: int, indent: int) -> tuple[dict, int]:
    data: dict[str, Any] = {}
    i = index
    while i < len(lines):
        current_indent, current_line = lines[i]
        if current_indent < indent:
            break
        if current_indent != indent:
            raise ValueError("YAML indentation is invalid.")
        if current_line.startswith("- "):
            raise ValueError("YAML list entry is not under a key.")
        if ":" not in current_line:
            raise ValueError("YAML mapping entry is invalid.")
        key, value = current_line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            raise ValueError("YAML mapping entry is missing a key.")
        if value:
            data[key] = _parse_yaml_scalar(value)
            i += 1
            continue
        i += 1
        if i >= len(lines) or lines[i][0] <= indent:
            data[key] = {}
            continue
        if lines[i][1].startswith("- "):
            list_value, i = _parse_yaml_list(lines, i, indent + 2)
            data[key] = list_value
        else:
            map_value, i = _parse_yaml_map(lines, i, indent + 2)
            data[key] = map_value
    return data, i


def _parse_yaml_list(lines: list[tuple[int, str]], index: int, indent: int) -> tuple[list, int]:
    items: list[Any] = []
    i = index
    while i < len(lines):
        current_indent, current_line = lines[i]
        if current_indent < indent:
            break
        if current_indent != indent:
            raise ValueError("YAML indentation is invalid.")
        if not current_line.startswith("- "):
            raise ValueError("YAML list entry is invalid.")
        value = current_line[2:].strip()
        if not value:
            i += 1
            if i >= len(lines) or lines[i][0] <= indent:
                items.append({})
                continue
            if lines[i][1].startswith("- "):
                nested, i = _parse_yaml_list(lines, i, indent + 2)
                items.append(nested)
            else:
                nested, i = _parse_yaml_map(lines, i, indent + 2)
                items.append(nested)
            continue
        if ":" in value:
            key, rest = value.split(":", 1)
            key = key.strip()
            rest = rest.strip()
            item: dict[str, Any] = {}
            if rest:
                item[key] = _parse_yaml_scalar(rest)
            else:
                item[key] = {}
            i += 1
            if i < len(lines) and lines[i][0] > indent:
                nested, i = _parse_yaml_map(lines, i, indent + 2)
                if isinstance(item.get(key), dict):
                    item[key].update(nested)
                else:
                    item.update(nested)
            items.append(item)
            continue
        items.append(_parse_yaml_scalar(value))
        i += 1
    return items, i


def _parse_yaml_scalar(value: str) -> Any:
    if value.startswith("\"") and value.endswith("\""):
        return value[1:-1]
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1]
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered == "null":
        return None
    if lowered.isdigit():
        return int(lowered)
    try:
        if "." in lowered:
            return float(lowered)
    except Exception:
        pass
    return value


def _render_yaml(value: object, *, indent: int) -> list[str]:
    prefix = " " * indent
    if isinstance(value, dict):
        lines: list[str] = []
        for key in sorted(value.keys(), key=lambda item: str(item)):
            item = value[key]
            if isinstance(item, (dict, list)):
                lines.append(f"{prefix}{_quote_key(key)}:")
                lines.extend(_render_yaml(item, indent=indent + 2))
            else:
                lines.append(f"{prefix}{_quote_key(key)}: {_format_scalar(item)}")
        return lines
    if isinstance(value, list):
        lines = []
        for item in value:
            if isinstance(item, (dict, list)):
                lines.append(f"{prefix}-")
                lines.extend(_render_yaml(item, indent=indent + 2))
            else:
                lines.append(f"{prefix}- {_format_scalar(item)}")
        return lines
    return [f"{prefix}{_format_scalar(value)}"]


def _quote_key(key: object) -> str:
    text = str(key)
    if _needs_quote(text):
        return _quote(text)
    return text


def _format_scalar(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    return _quote(text) if _needs_quote(text) else text


def _needs_quote(text: str) -> bool:
    if not text:
        return True
    for ch in text:
        if ch.isspace():
            return True
    return any(ch in text for ch in [":", "#", "{", "}", "[", "]", "\"", "'"])


def _quote(text: str) -> str:
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f"\"{escaped}\""


__all__ = ["parse_yaml", "render_yaml"]
