from __future__ import annotations

from typing import Dict, Iterable, List

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.module_loader.resolve import collect_definitions, qualify, resolve_program
from namel3ss.module_loader.types import ModuleExports, ModuleInfo


def _merge_programs(
    app_ast: ast.Program,
    modules: Dict[str, ModuleInfo],
    app_aliases: Dict[str, str],
    module_defs: Dict[str, Dict[str, set[str]]],
    exports_map: Dict[str, ModuleExports],
    module_order: List[str],
    *,
    extra_defs: Dict[str, set[str]] | None = None,
) -> ast.Program:
    local_defs = collect_definitions([app_ast])
    if extra_defs:
        for kind, names in extra_defs.items():
            local_defs.setdefault(kind, set()).update(names)
    resolve_program(
        app_ast,
        module_name=None,
        alias_map=app_aliases,
        local_defs=local_defs,
        exports_map=exports_map,
        context_label="App",
    )

    combined_records = list(app_ast.records)
    combined_functions = list(getattr(app_ast, "functions", []))
    combined_flows = list(app_ast.flows)
    combined_jobs = list(getattr(app_ast, "jobs", []))
    combined_pages = list(app_ast.pages)
    combined_ui_packs = list(getattr(app_ast, "ui_packs", []))
    combined_ais = list(app_ast.ais)
    combined_tools = list(app_ast.tools)
    combined_agents = list(app_ast.agents)
    agent_team = getattr(app_ast, "agent_team", None)
    identity_decl = app_ast.identity

    for name in module_order:
        info = modules[name]
        local_defs = module_defs[name]
        alias_map = _normalize_uses(info.uses, context_label=f"Module {name}")
        for program in info.programs:
            if program.identity is not None:
                raise Namel3ssError(
                    build_guidance_message(
                        what="Identity declarations are only allowed in app.ai.",
                        why=f"Module '{name}' defines an identity block.",
                        fix="Move the identity declaration to app.ai.",
                        example='identity "user":',
                    ),
                )
            if getattr(program, "agent_team", None) is not None:
                raise Namel3ssError(
                    build_guidance_message(
                        what="Team of agents is only allowed in app.ai.",
                        why=f"Module '{name}' defines a team of agents block.",
                        fix="Move the team of agents block into app.ai.",
                        example='team of agents\n  "planner"',
                    ),
                )
            resolve_program(
                program,
                module_name=name,
                alias_map=alias_map,
                local_defs=local_defs,
                exports_map=exports_map,
                context_label=f"Module {name}",
            )
            combined_records.extend(program.records)
            combined_functions.extend(getattr(program, "functions", []))
            combined_flows.extend(program.flows)
            combined_jobs.extend(getattr(program, "jobs", []))
            combined_ais.extend(program.ais)
            combined_tools.extend(program.tools)
            combined_agents.extend(program.agents)
            combined_pages.extend(_exported_pages(program.pages, name, exports_map))
            combined_ui_packs.extend(_exported_ui_packs(getattr(program, "ui_packs", []), name, exports_map))

    combined = ast.Program(
        spec_version=app_ast.spec_version,
        app_theme=app_ast.app_theme,
        app_theme_line=app_ast.app_theme_line,
        app_theme_column=app_ast.app_theme_column,
        theme_tokens=app_ast.theme_tokens,
        theme_preference=app_ast.theme_preference,
        ui_settings=app_ast.ui_settings,
        ui_line=getattr(app_ast, "ui_line", None),
        ui_column=getattr(app_ast, "ui_column", None),
        capabilities=list(getattr(app_ast, "capabilities", []) or []),
        records=combined_records,
        functions=combined_functions,
        contracts=list(getattr(app_ast, "contracts", []) or []),
        flows=combined_flows,
        jobs=combined_jobs,
        pages=combined_pages,
        ui_packs=combined_ui_packs,
        ais=combined_ais,
        tools=combined_tools,
        agents=combined_agents,
        agent_team=agent_team,
        uses=[],
        capsule=None,
        identity=identity_decl,
        line=app_ast.line,
        column=app_ast.column,
    )
    raw_allowlist = getattr(app_ast, "pack_allowlist", None)
    setattr(combined, "pack_allowlist", list(raw_allowlist) if raw_allowlist is not None else None)
    return combined


def _exported_pages(
    pages: List[ast.PageDecl],
    module_name: str,
    exports_map: Dict[str, ModuleExports],
) -> List[ast.PageDecl]:
    exported = exports_map.get(module_name, ModuleExports()).by_kind.get("page", set())
    if not exported:
        return []
    allowed = {qualify(module_name, name) for name in exported}
    return [page for page in pages if page.name in allowed]


def _exported_ui_packs(
    packs: List[ast.UIPackDecl],
    module_name: str,
    exports_map: Dict[str, ModuleExports],
) -> List[ast.UIPackDecl]:
    exported = exports_map.get(module_name, ModuleExports()).by_kind.get("ui_pack", set())
    if not exported:
        return []
    allowed = {qualify(module_name, name) for name in exported}
    return [pack for pack in packs if pack.name in allowed]


def _public_flow_names(
    app_ast: ast.Program,
    modules: Dict[str, ModuleInfo],
    exports_map: Dict[str, ModuleExports],
) -> List[str]:
    names = [flow.name for flow in app_ast.flows]
    for module_name, exports in exports_map.items():
        for flow_name in exports.by_kind.get("flow", set()):
            names.append(qualify(module_name, flow_name))
    return sorted(set(names))


def _build_exports(modules: Dict[str, ModuleInfo]) -> Dict[str, ModuleExports]:
    return {name: info.exports for name, info in modules.items()}


def _validate_exports(modules: Dict[str, ModuleInfo], module_defs: Dict[str, Dict[str, set[str]]]) -> None:
    for module_name, info in modules.items():
        defs = module_defs.get(module_name, {})
        for kind, names in info.exports.by_kind.items():
            for name in names:
                if name not in defs.get(kind, set()):
                    raise Namel3ssError(
                        build_guidance_message(
                            what=f"Exported {kind} '{name}' not found in module '{module_name}'.",
                            why="Capsule exports must match declarations in the module files.",
                            fix="Define the symbol or remove it from exports.",
                            example=f'{kind} "{name}"',
                        ),
                        line=info.capsule.line,
                        column=info.capsule.column,
                    )


def _module_dependencies(info: ModuleInfo) -> List[str]:
    return sorted({use.module for use in info.uses})


def _normalize_uses(uses: Iterable[ast.UseDecl], *, context_label: str) -> Dict[str, str]:
    alias_map: Dict[str, str] = {}
    module_map: Dict[str, str] = {}
    for use in uses:
        if use.alias in alias_map and alias_map[use.alias] != use.module:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Alias '{use.alias}' is already used in {context_label}.",
                    why="Each alias must map to a single module.",
                    fix="Pick a different alias for the second module.",
                    example='use "inventory" as inv',
                ),
                line=use.line,
                column=use.column,
            )
        if use.module in module_map and module_map[use.module] != use.alias:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Module '{use.module}' is imported more than once.",
                    why="Each module should be imported with a single alias.",
                    fix="Remove the duplicate use statement.",
                    example=f'use "{use.module}" as {module_map[use.module]}',
                ),
                line=use.line,
                column=use.column,
            )
        alias_map[use.alias] = use.module
        module_map[use.module] = use.alias
    return alias_map


__all__ = [
    "_build_exports",
    "_merge_programs",
    "_module_dependencies",
    "_normalize_uses",
    "_public_flow_names",
    "_validate_exports",
]
