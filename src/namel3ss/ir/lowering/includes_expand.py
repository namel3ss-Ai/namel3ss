from __future__ import annotations

from copy import deepcopy
from hashlib import sha256

from namel3ss.ast import nodes as ast
from namel3ss.parser.program_loader import IncludeProgramEntry


def compose_program_with_includes(
    *,
    root_program: ast.Program,
    include_entries: tuple[IncludeProgramEntry, ...] | list[IncludeProgramEntry],
) -> ast.Program:
    if not include_entries:
        return root_program
    combined = deepcopy(root_program)
    source_map_entries: list[dict[str, object]] = []
    for entry in include_entries:
        include_program = entry.program
        _extend_list(combined.functions, include_program.functions)
        _extend_list(combined.records, include_program.records)
        _extend_list(combined.contracts, include_program.contracts)
        _extend_list(combined.flows, include_program.flows)
        _extend_list(combined.routes, include_program.routes)
        _extend_list(combined.crud, include_program.crud)
        _extend_list(combined.prompts, include_program.prompts)
        _extend_list(combined.ai_flows, include_program.ai_flows)
        _extend_list(combined.jobs, include_program.jobs)
        _extend_list(combined.ais, include_program.ais)
        _extend_list(combined.tools, include_program.tools)
        _extend_list(combined.agents, include_program.agents)
        _extend_list(combined.ui_packs, include_program.ui_packs)
        _extend_list(combined.ui_patterns, include_program.ui_patterns)
        _extend_list(combined.uses, include_program.uses)
        _extend_plugin_uses(combined.plugin_uses, include_program.plugin_uses)
        source_map_entries.extend(_build_source_map_entries(entry))
    source_map_entries.sort(key=lambda item: str(item.get("decl_id") or ""))
    setattr(combined, "composition_source_map", source_map_entries)
    setattr(combined, "composed_include_paths", [entry.path_norm for entry in include_entries])
    return combined


def _build_source_map_entries(entry: IncludeProgramEntry) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for kind, items in (
        ("function", entry.program.functions),
        ("record", entry.program.records),
        ("contract", entry.program.contracts),
        ("flow", entry.program.flows),
        ("route", entry.program.routes),
        ("crud", entry.program.crud),
        ("prompt", entry.program.prompts),
        ("ai_flow", entry.program.ai_flows),
        ("job", entry.program.jobs),
        ("ai", entry.program.ais),
        ("tool", entry.program.tools),
        ("agent", entry.program.agents),
        ("ui_pack", entry.program.ui_packs),
        ("ui_pattern", entry.program.ui_patterns),
    ):
        rows.extend(_entries_for_kind(entry, kind=kind, items=items))
    return rows


def _entries_for_kind(entry: IncludeProgramEntry, *, kind: str, items: list[object]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for local_index, item in enumerate(items):
        name = getattr(item, "name", None)
        if not isinstance(name, str) or not name.strip():
            continue
        decl_hash = _decl_hash(
            include_index=entry.include_index,
            file=entry.path_norm,
            kind=kind,
            name=name,
            local_index=local_index,
        )
        rows.append(
            {
                "decl_id": f"inc-{entry.include_index:03d}-{kind}-{decl_hash}",
                "file": entry.path_norm,
                "line": _line_value(getattr(item, "line", None)),
                "col": _line_value(getattr(item, "column", None)),
            }
        )
    return rows


def _decl_hash(*, include_index: int, file: str, kind: str, name: str, local_index: int) -> str:
    payload = f"{include_index}:{file}:{kind}:{name}:{local_index}"
    return sha256(payload.encode("utf-8")).hexdigest()[:12]


def _line_value(value: object) -> int:
    if isinstance(value, int) and value > 0:
        return value
    return 1


def _extend_list(target: list, source: list) -> None:
    for item in source:
        target.append(item)


def _extend_plugin_uses(target: list[ast.PluginUseDecl], source: list[ast.PluginUseDecl]) -> None:
    seen = {str(getattr(item, "name", "") or "") for item in target}
    for item in source:
        name = str(getattr(item, "name", "") or "")
        if not name or name in seen:
            continue
        seen.add(name)
        target.append(item)


__all__ = ["compose_program_with_includes"]
