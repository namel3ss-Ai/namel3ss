from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ir.nodes import lower_program
from namel3ss.module_loader.graph import build_graph, topo_sort
from namel3ss.module_loader.source_io import (
    ParseCache,
    SourceOverrides,
    _has_override,
    _parse_source,
    _read_source,
)
from namel3ss.module_loader.resolve import collect_definitions, qualify, resolve_program
from namel3ss.module_loader.types import ModuleExports, ModuleInfo, ProjectLoadResult
from namel3ss.module_loader.module_files import (
    apply_module_file_results,
    collect_module_file_defs,
    load_module_file_results,
)
from namel3ss.ui.external.detect import detect_external_ui


ROOT_NODE = "(app)"


def load_project(
    app_path: str | Path,
    *,
    allow_legacy_type_aliases: bool = True,
    extra_uses: Iterable[ast.UseDecl] | None = None,
    source_overrides: SourceOverrides | None = None,
    parse_cache: ParseCache | None = None,
) -> ProjectLoadResult:
    app_file = Path(app_path)
    if not app_file.exists() and not _has_override(app_file, source_overrides):
        raise Namel3ssError(
            build_guidance_message(
                what=f"App file not found: {app_file.as_posix()}",
                why="The path does not point to an existing .ai file.",
                fix="Check the path or run commands from the project directory.",
                example="n3 app.ai check",
            )
        )
    root = app_file.parent
    sources: Dict[Path, str] = {}

    app_source = _read_source(app_file, source_overrides)
    sources[app_file] = app_source
    app_ast = _parse_source(
        app_source,
        app_file,
        allow_legacy_type_aliases=allow_legacy_type_aliases,
        parse_cache=parse_cache,
    )

    app_uses = list(app_ast.uses)
    legacy_app_uses = [use for use in app_uses if not use.module_path]
    module_file_uses = [use for use in app_uses if use.module_path]
    app_aliases = _normalize_uses(legacy_app_uses, context_label="App")
    load_uses = list(legacy_app_uses)
    if extra_uses:
        extra_list = list(extra_uses)
        legacy_extra = [use for use in extra_list if not use.module_path]
        module_extra = [use for use in extra_list if use.module_path]
        load_uses.extend(legacy_extra)
        module_file_uses.extend(module_extra)

    modules: Dict[str, ModuleInfo] = {}
    for use in load_uses:
        _load_module(
            use.module,
            root,
            modules,
            sources,
            allow_legacy_type_aliases=allow_legacy_type_aliases,
            source_overrides=source_overrides,
            parse_cache=parse_cache,
        )

    edges = [(name, dep) for name, info in modules.items() for dep in _module_dependencies(info)]
    graph = build_graph(modules.keys(), edges)
    module_order = topo_sort(graph)

    exports_map = _build_exports(modules)
    module_defs = {name: collect_definitions(info.programs) for name, info in modules.items()}
    _validate_exports(modules, module_defs)

    module_file_results, module_file_sources = load_module_file_results(
        root,
        module_file_uses,
        allow_legacy_type_aliases=allow_legacy_type_aliases,
        spec_version=app_ast.spec_version,
    )
    module_file_defs = collect_module_file_defs(module_file_results)

    combined = _merge_programs(
        app_ast,
        modules,
        app_aliases,
        module_defs,
        exports_map,
        module_order,
        extra_defs=module_file_defs,
    )
    program_ir = lower_program(combined)
    setattr(program_ir, "project_root", root)
    setattr(program_ir, "app_path", app_file)
    setattr(program_ir, "external_ui_enabled", detect_external_ui(root, app_file))

    public_flows = _public_flow_names(app_ast, modules, exports_map)
    entry_flows = [flow.name for flow in app_ast.flows]
    setattr(program_ir, "public_flows", public_flows)
    setattr(program_ir, "entry_flows", entry_flows)

    program_ir = apply_module_file_results(
        program_ir,
        module_file_results=module_file_results,
        module_file_sources=module_file_sources,
        sources=sources,
        app_path=app_file,
    )

    graph_with_root = build_graph(
        [ROOT_NODE, *modules.keys()],
        [(ROOT_NODE, use.module) for use in legacy_app_uses] + edges,
    )

    return ProjectLoadResult(
        program=program_ir,
        app_path=app_file,
        sources=sources,
        app_ast=app_ast,
        modules=modules,
        graph=graph_with_root,
        public_flows=public_flows,
    )


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
    combined_pages = list(app_ast.pages)
    combined_ui_packs = list(getattr(app_ast, "ui_packs", []))
    combined_ais = list(app_ast.ais)
    combined_tools = list(app_ast.tools)
    combined_agents = list(app_ast.agents)
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
                        example='identity \"user\":',
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
            combined_ais.extend(program.ais)
            combined_tools.extend(program.tools)
            combined_agents.extend(program.agents)
            combined_pages.extend(_exported_pages(program.pages, name, exports_map))
            combined_ui_packs.extend(_exported_ui_packs(getattr(program, "ui_packs", []), name, exports_map))

    return ast.Program(
        spec_version=app_ast.spec_version,
        app_theme=app_ast.app_theme,
        app_theme_line=app_ast.app_theme_line,
        app_theme_column=app_ast.app_theme_column,
        theme_tokens=app_ast.theme_tokens,
        theme_preference=app_ast.theme_preference,
        records=combined_records,
        functions=combined_functions,
        flows=combined_flows,
        pages=combined_pages,
        ui_packs=combined_ui_packs,
        ais=combined_ais,
        tools=combined_tools,
        agents=combined_agents,
        uses=[],
        capsule=None,
        identity=identity_decl,
        line=app_ast.line,
        column=app_ast.column,
    )


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


def _load_module(
    module_name: str,
    root: Path,
    modules: Dict[str, ModuleInfo],
    sources: Dict[Path, str],
    *,
    allow_legacy_type_aliases: bool,
    source_overrides: SourceOverrides | None,
    parse_cache: ParseCache | None,
) -> None:
    if module_name in modules:
        return
    module_dir, capsule_path = _resolve_module_dir(root, module_name, source_overrides)
    capsule_source = _read_source(capsule_path, source_overrides)
    sources[capsule_path] = capsule_source
    capsule_program = _parse_source(
        capsule_source,
        capsule_path,
        allow_legacy_type_aliases=allow_legacy_type_aliases,
        allow_capsule=True,
        require_spec=False,
        parse_cache=parse_cache,
    )
    if capsule_program.capsule is None:
        raise Namel3ssError(
            build_guidance_message(
                what=f"Capsule file for '{module_name}' is missing a capsule declaration.",
                why="Each module must declare its capsule name and exports.",
                fix='Add `capsule "<name>":` and an exports block.',
                example=f'capsule "{module_name}":',
            )
        )
    capsule_decl = capsule_program.capsule
    if capsule_decl.name != module_name:
        raise Namel3ssError(
            build_guidance_message(
                what="Capsule name does not match module folder.",
                why=f'capsule.ai declares "{capsule_decl.name}" but the folder is "{module_name}".',
                fix="Update the capsule name to match the folder.",
                example=f'capsule "{module_name}":',
            ),
            line=capsule_decl.line,
            column=capsule_decl.column,
        )
    programs = []
    files = _collect_module_files(module_dir, source_overrides)
    for path in files:
        source = _read_source(path, source_overrides)
        sources[path] = source
        program = _parse_source(
            source,
            path,
            allow_legacy_type_aliases=allow_legacy_type_aliases,
            require_spec=False,
            parse_cache=parse_cache,
        )
        if program.app_theme_line is not None:
            raise Namel3ssError(
                build_guidance_message(
                    what="App declarations are not allowed inside modules.",
                    why="Only the root app.ai file defines the app theme and UI shell.",
                    fix="Move the app declaration to app.ai.",
                    example="app:\n  theme is \"system\"",
                ),
                line=program.app_theme_line,
                column=program.app_theme_column,
            )
        programs.append(program)

    uses = list(capsule_program.uses)
    for program in programs:
        uses.extend(program.uses)
    module_file_uses = [use for use in uses if use.module_path]
    if module_file_uses:
        first = module_file_uses[0]
        raise Namel3ssError(
            build_guidance_message(
                what="Use module is not allowed inside capsule modules.",
                why="Capsule modules only import other capsules.",
                fix="Move use module statements to app.ai.",
                example='use module "modules/common.ai" as common',
            ),
            line=first.line,
            column=first.column,
        )
    uses = [use for use in uses if not use.module_path]

    exports = ModuleExports()
    for export in capsule_decl.exports:
        exports.add(export.kind, export.name)

    modules[module_name] = ModuleInfo(
        name=module_name,
        path=module_dir,
        capsule=capsule_decl,
        uses=uses,
        programs=programs,
        exports=exports,
        files=files,
    )

    for use in uses:
        _load_module(
            use.module,
            root,
            modules,
            sources,
            allow_legacy_type_aliases=allow_legacy_type_aliases,
            source_overrides=source_overrides,
            parse_cache=parse_cache,
        )


def _resolve_module_dir(root: Path, module_name: str, source_overrides: SourceOverrides | None) -> tuple[Path, Path]:
    module_dir = root / "modules" / module_name
    capsule_path = module_dir / "capsule.ai"
    if capsule_path.exists() or _has_override(capsule_path, source_overrides):
        return module_dir, capsule_path
    package_dir = root / "packages" / module_name
    package_capsule = package_dir / "capsule.ai"
    if package_capsule.exists() or _has_override(package_capsule, source_overrides):
        return package_dir, package_capsule
    raise Namel3ssError(
        build_guidance_message(
            what=f"Module '{module_name}' was not found.",
            why=(
                f"No capsule.ai exists at {capsule_path.as_posix()} "
                f"or {package_capsule.as_posix()}."
            ),
            fix=f"Create modules/{module_name}/capsule.ai or install the package.",
            example=f'modules/{module_name}/capsule.ai',
        )
    )


def _collect_module_files(module_dir: Path, source_overrides: SourceOverrides | None) -> List[Path]:
    files = []
    for path in module_dir.rglob("*.ai"):
        if path.name in {"capsule.ai", "app.ai"}:
            continue
        if path.name.endswith("_test.ai"):
            continue
        relative_parts = {part.lower() for part in path.relative_to(module_dir).parts}
        if "tests" in relative_parts or "examples" in relative_parts or "example" in relative_parts:
            continue
        files.append(path)
    if source_overrides:
        for path in source_overrides.keys():
            if path.name in {"capsule.ai", "app.ai"} or path.suffix != ".ai":
                continue
            try:
                rel_parts = {part.lower() for part in path.relative_to(module_dir).parts}
            except ValueError:
                continue
            if "tests" in rel_parts or "examples" in rel_parts or "example" in rel_parts or path.name.endswith("_test.ai"):
                continue
            files.append(path)
    return sorted(files, key=lambda p: p.relative_to(module_dir).as_posix())


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
