from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ir.lowering.includes_expand import compose_program_with_includes
from namel3ss.ir.nodes import lower_program
from namel3ss.ir.validation.duplicate_symbols_validation import validate_duplicate_symbols
from namel3ss.ir.validation.includes_validation import ensure_include_capability, normalize_include_warnings
from namel3ss.ir.validation.root_authority_validation import validate_root_authority
from namel3ss.module_loader.graph import build_graph, topo_sort
from namel3ss.module_loader.module_files import (
    apply_module_file_results,
    collect_module_file_defs,
    load_module_file_results,
)
from namel3ss.module_loader.parse import _load_module
from namel3ss.module_loader.resolve import collect_definitions
from namel3ss.module_loader.source_io import ParseCache, SourceOverrides, _has_override, _parse_source, _read_source
from namel3ss.module_loader.static import (
    _build_exports,
    _merge_programs,
    _module_dependencies,
    _normalize_uses,
    _public_flow_names,
    _validate_exports,
)
from namel3ss.module_loader.types import ModuleInfo, ProjectLoadResult
from namel3ss.ui.external.detect import detect_external_ui
from namel3ss.parser.program_loader import load_included_programs

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
    ensure_include_capability(app_ast)
    include_result = load_included_programs(
        root_program=app_ast,
        root_file=app_file,
        read_source=lambda path: _read_source(path, source_overrides),
        parse_source=lambda source, path: _parse_source(
            source,
            path,
            allow_legacy_type_aliases=allow_legacy_type_aliases,
            require_spec=False,
            parse_cache=parse_cache,
        ),
    )
    validate_root_authority(include_result.entries)
    validate_duplicate_symbols(
        root_program=app_ast,
        root_path=app_file.name,
        include_entries=include_result.entries,
    )
    for include_entry in include_result.entries:
        sources[include_entry.path] = _read_source(include_entry.path, source_overrides)
    app_ast = compose_program_with_includes(
        root_program=app_ast,
        include_entries=list(include_result.entries),
    )
    include_warnings = normalize_include_warnings(include_result.warnings)
    if include_warnings:
        setattr(app_ast, "composition_include_warnings", include_warnings)
    if getattr(app_ast, "composition_source_map", None):
        setattr(app_ast, "composition_source_map", list(getattr(app_ast, "composition_source_map", []) or []))

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
    setattr(combined, "project_root", root)
    setattr(combined, "app_path", app_file)
    program_ir = lower_program(combined)
    setattr(program_ir, "composition_include_warnings", list(getattr(app_ast, "composition_include_warnings", []) or []))
    setattr(program_ir, "composition_source_map", list(getattr(app_ast, "composition_source_map", []) or []))
    setattr(program_ir, "composed_include_paths", list(getattr(app_ast, "composed_include_paths", []) or []))
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


__all__ = ["load_project"]
