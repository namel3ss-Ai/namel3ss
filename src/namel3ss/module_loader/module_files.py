from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, Tuple

from namel3ss.ast import nodes as ast
from namel3ss.ir import nodes as ir
from namel3ss.runtime.modules.loader import load_modules as load_module_files
from namel3ss.runtime.modules.merge import merge_modules as merge_module_files
from namel3ss.runtime.modules.sources import flatten_sources as flatten_module_sources, source_info_dict
from namel3ss.runtime.modules.traces import build_module_traces


def load_module_file_results(
    project_root: Path,
    uses: Iterable[ast.UseDecl],
    *,
    allow_legacy_type_aliases: bool,
    spec_version: str | None,
) -> Tuple[list, Dict[Path, str]]:
    return load_module_files(
        project_root,
        uses,
        allow_legacy_type_aliases=allow_legacy_type_aliases,
        spec_version=spec_version,
    )


def apply_module_file_results(
    program_ir: ir.Program,
    *,
    module_file_results: list,
    module_file_sources: Dict[Path, str],
    sources: Dict[Path, str],
    app_path: Path,
) -> ir.Program:
    sources.update(module_file_sources)
    if not module_file_results:
        return program_ir

    merge_result = merge_module_files(program_ir, module_file_results, app_path=app_path)
    program_ir = merge_result.program
    module_traces = build_module_traces(merge_result.modules, merge_result.overrides)
    setattr(program_ir, "module_traces", module_traces)
    setattr(program_ir, "module_sources", flatten_module_sources(merge_result.sources))
    setattr(program_ir, "module_summary", _build_module_summary(merge_result))
    return program_ir


def collect_module_file_defs(module_file_results: list) -> Dict[str, set[str]]:
    defs: Dict[str, set[str]] = {
        "record": set(),
        "function": set(),
        "tool": set(),
        "page": set(),
    }
    for result in module_file_results:
        defs["function"].update(result.program.functions.keys())
        defs["record"].update(rec.name for rec in result.program.records)
        defs["tool"].update(result.program.tools.keys())
        defs["page"].update(page.name for page in result.program.pages)
    return defs


def _build_module_summary(merge_result) -> dict:
    modules = []
    for module in merge_result.modules:
        modules.append(
            {
                "module_id": module.module_id,
                "module_name": module.module_name,
                "module_alias": module.alias,
                "path": module.path.as_posix(),
                "provided": module.provided,
                "only": list(module.selection.only),
                "allow_override": list(module.selection.allow_override),
            }
        )
    overrides = [
        {
            "kind": entry.kind,
            "name": entry.name,
            "previous": source_info_dict(entry.previous),
            "current": source_info_dict(entry.current),
        }
        for entry in merge_result.overrides
    ]
    return {
        "modules": modules,
        "merge_order": [module.alias for module in merge_result.modules],
        "overrides": overrides,
    }


__all__ = ["apply_module_file_results", "collect_module_file_defs", "load_module_file_results"]
