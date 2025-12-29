from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ir.nodes import lower_program
from namel3ss.parser.core import parse
from namel3ss.runtime.modules.format import ModuleLoadResult, ModuleSelection, MODULE_CATEGORIES
from namel3ss.runtime.modules.resolver import module_id_for_path, resolve_module_path
from namel3ss.runtime.modules.validate import validate_module_program


def load_modules(
    project_root: Path,
    uses: Iterable[ast.UseDecl],
    *,
    allow_legacy_type_aliases: bool,
    spec_version: str | None = None,
) -> Tuple[List[ModuleLoadResult], Dict[Path, str]]:
    results: List[ModuleLoadResult] = []
    sources: Dict[Path, str] = {}
    alias_map: Dict[str, str] = {}
    module_map: Dict[str, str] = {}

    for use in uses:
        if not use.module_path:
            continue
        raw_path = use.module_path
        path = resolve_module_path(project_root, raw_path)
        module_id = module_id_for_path(project_root, path)
        if use.alias in alias_map and alias_map[use.alias] != module_id:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Alias {use.alias} is already used.",
                    why="Each module alias must be unique.",
                    fix="Pick a different alias for the second module.",
                    example='use module "modules/common.ai" as common',
                ),
                line=use.line,
                column=use.column,
            )
        if module_id in module_map and module_map[module_id] != use.alias:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Module {module_id} is imported more than once.",
                    why="Each module path must map to a single alias.",
                    fix="Remove the duplicate use module statement.",
                    example='use module "modules/common.ai" as common',
                ),
                line=use.line,
                column=use.column,
            )
        alias_map[use.alias] = module_id
        module_map[module_id] = use.alias
        try:
            source = path.read_text(encoding="utf-8")
        except FileNotFoundError as err:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Module file not found at {path.as_posix()}.",
                    why="The module path did not match a file on disk.",
                    fix="Check the path or create the module file.",
                    example='use module "modules/common.ai" as common',
                ),
                line=use.line,
                column=use.column,
            ) from err
        sources[path] = source
        program_ast = parse(
            source,
            allow_legacy_type_aliases=allow_legacy_type_aliases,
            require_spec=False,
        )
        if spec_version and not program_ast.spec_version:
            program_ast.spec_version = spec_version
        validate_module_program(program_ast, path=path)
        program_ir = lower_program(program_ast)
        selection = ModuleSelection(
            only=_normalize_categories(use.only),
            allow_override=_normalize_categories(use.allow_override),
        )
        provided = _select_provided(program_ir, selection.only)
        results.append(
            ModuleLoadResult(
                module_id=module_id,
                module_name=use.alias,
                alias=use.alias,
                path=path,
                program=program_ir,
                provided=provided,
                selection=selection,
            )
        )
    return results, sources


def _normalize_categories(values: List[str]) -> tuple[str, ...]:
    if not values:
        return ()
    order = {name: idx for idx, name in enumerate(MODULE_CATEGORIES)}
    unique = []
    for value in values:
        if value not in order:
            continue
        if value in unique:
            continue
        unique.append(value)
    return tuple(sorted(unique, key=lambda item: order[item]))


def _select_provided(program, only: tuple[str, ...]) -> Dict[str, List[str]]:
    all_items = {
        "functions": sorted(program.functions.keys()),
        "records": sorted([rec.name for rec in program.records]),
        "tools": sorted(program.tools.keys()),
        "pages": sorted([page.name for page in program.pages]),
    }
    selected = list(only) if only else list(MODULE_CATEGORIES)
    provided: Dict[str, List[str]] = {}
    for category in MODULE_CATEGORIES:
        if category not in selected:
            continue
        names = all_items.get(category, [])
        if names:
            provided[category] = names
    return provided


__all__ = ["load_modules"]
