from __future__ import annotations

from collections.abc import Iterable

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.parser.program_loader import IncludeProgramEntry


def validate_duplicate_symbols(
    *,
    root_program: ast.Program,
    root_path: str,
    include_entries: Iterable[IncludeProgramEntry],
) -> None:
    seen: dict[tuple[str, str], str] = {}
    for kind, name in _iter_symbol_names(root_program):
        if not kind or not name:
            continue
        seen[(kind, name)] = root_path
    for entry in include_entries:
        current_path = entry.path_norm
        for kind, name in _iter_symbol_names(entry.program):
            if not kind or not name:
                continue
            previous = seen.get((kind, name))
            if previous is not None:
                raise Namel3ssError(
                    f'Compile error: duplicate declaration \'{name}\' found in "{current_path}" '
                    f'(already defined in "{previous}")'
                )
            seen[(kind, name)] = current_path


def _iter_symbol_names(program: ast.Program) -> list[tuple[str, str]]:
    names: list[tuple[str, str]] = []
    names.extend(_names_from_nodes(getattr(program, "functions", []) or [], kind="function"))
    names.extend(_names_from_nodes(getattr(program, "records", []) or [], kind="record"))
    names.extend(_names_from_nodes(getattr(program, "flows", []) or [], kind="flow"))
    names.extend(_names_from_nodes(getattr(program, "routes", []) or [], kind="route"))
    names.extend(_names_from_nodes(getattr(program, "crud", []) or [], kind="crud"))
    names.extend(_names_from_nodes(getattr(program, "prompts", []) or [], kind="prompt"))
    names.extend(_names_from_nodes(getattr(program, "ai_flows", []) or [], kind="ai_flow"))
    names.extend(_names_from_nodes(getattr(program, "jobs", []) or [], kind="job"))
    names.extend(_names_from_nodes(getattr(program, "ais", []) or [], kind="ai"))
    names.extend(_names_from_nodes(getattr(program, "tools", []) or [], kind="tool"))
    names.extend(_names_from_nodes(getattr(program, "agents", []) or [], kind="agent"))
    names.extend(_names_from_nodes(getattr(program, "ui_packs", []) or [], kind="ui_pack"))
    names.extend(_names_from_nodes(getattr(program, "ui_patterns", []) or [], kind="ui_pattern"))
    return names


def _names_from_nodes(items: Iterable[object], *, kind: str) -> list[tuple[str, str]]:
    names: list[tuple[str, str]] = []
    for item in items:
        name = getattr(item, "name", None)
        if isinstance(name, str) and name.strip():
            names.append((kind, name.strip()))
    return names


__all__ = ["validate_duplicate_symbols"]
