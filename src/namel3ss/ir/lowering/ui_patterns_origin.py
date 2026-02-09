from __future__ import annotations

from dataclasses import dataclass

from namel3ss.ast import nodes as ast
from namel3ss.ui.patterns.model import PatternDefinition


@dataclass(frozen=True)
class PatternContext:
    name: str
    invocation_id: str
    parameters: dict[str, object]


def _merge_origin(base: dict | None, override: dict | None) -> dict | None:
    if base is None and override is None:
        return None
    merged: dict = {}
    if base:
        merged.update(base)
    if override:
        merged.update(override)
    return merged


def _attach_pattern_origin(
    item: ast.PageItem,
    context: PatternContext,
    element_path: list[int],
    base_origin: dict | None,
) -> ast.PageItem:
    existing = getattr(item, "origin", None)
    origin = _merge_origin(base_origin, existing) or {}
    origin.update(
        {
            "pattern": context.name,
            "invocation": context.invocation_id,
            "element": _format_element_path(element_path),
            "parameters": context.parameters,
        }
    )
    setattr(item, "origin", origin)
    return item


def _pattern_parameters(pattern: PatternDefinition, values: dict[str, object]) -> dict[str, object]:
    ordered: dict[str, object] = {}
    for param in pattern.parameters:
        ordered[param.name] = _sanitize_param_value(values.get(param.name))
    return ordered


def _sanitize_param_value(value: object) -> object:
    if value is None:
        return None
    if isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, ast.StatePath):
        return _truncate_text(f"state.{'.'.join(value.path)}")
    if isinstance(value, str):
        return _truncate_text(value)
    return _truncate_text(str(value))


def _truncate_text(value: str, limit: int = 80) -> str:
    cleaned = " ".join(str(value).split())
    if _looks_like_path(cleaned):
        return "<redacted>"
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[: max(0, limit - 3)]}..."


def _looks_like_path(value: str) -> bool:
    if value.startswith(("/", "\\", "~")):
        return True
    if len(value) >= 3 and value[1] == ":" and value[0].isalpha() and value[2] in {"/", "\\"}:
        return True
    return False


def _format_invocation_id(page_name: str, path: list[int]) -> str:
    path_text = ".".join(str(entry) for entry in path)
    return f"page:{page_name}:pattern:{path_text}" if path_text else f"page:{page_name}:pattern"


def _format_element_path(path: list[int]) -> str:
    return ".".join(str(entry) for entry in path)


__all__ = [
    "PatternContext",
    "_attach_pattern_origin",
    "_format_invocation_id",
    "_format_element_path",
    "_merge_origin",
    "_pattern_parameters",
]
