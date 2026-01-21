from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple

from namel3ss.ast import nodes as ast
from namel3ss.module_loader.types import ProjectLoadResult

from namel3ss.editor.io import (
    FileIndex,
    ProjectIndex,
    SymbolDefinition,
    SymbolReference,
    _module_context,
    _scan_file,
)


def build_index(project: ProjectLoadResult) -> ProjectIndex:
    root = project.app_path.parent.resolve()
    exports = {name: info.exports for name, info in project.modules.items()}
    files: Dict[Path, FileIndex] = {}
    definitions: Dict[Tuple[str | None, str, str], SymbolDefinition] = {}
    nodes = _build_node_index(project)

    for path, source in project.sources.items():
        module_name, origin = _module_context(path, root)
        file_index = _scan_file(
            path=path,
            source=source,
            module_name=module_name,
            origin=origin,
            exports=exports,
        )
        files[path] = file_index
        for definition in file_index.definitions:
            key = (definition.module, definition.kind, definition.name)
            definitions[key] = definition

    return ProjectIndex(root=root, files=files, definitions=definitions, nodes=nodes, exports=exports)


def _build_node_index(project: ProjectLoadResult) -> Dict[Tuple[str | None, str, str], ast.Node]:
    nodes: Dict[Tuple[str | None, str, str], ast.Node] = {}
    app = project.app_ast
    _add_program_nodes(nodes, None, app)
    if app.identity:
        nodes[(None, "identity", app.identity.name)] = app.identity
    for module_name, info in project.modules.items():
        for program in info.programs:
            _add_program_nodes(nodes, module_name, program)
        if info.capsule:
            nodes[(None, "capsule", info.capsule.name)] = info.capsule
    return nodes


def _add_program_nodes(
    nodes: Dict[Tuple[str | None, str, str], ast.Node],
    module_name: str | None,
    program: ast.Program,
) -> None:
    for record in program.records:
        nodes[(module_name, "record", _local_name(module_name, record.name))] = record
    for flow in program.flows:
        nodes[(module_name, "flow", _local_name(module_name, flow.name))] = flow
    for job in getattr(program, "jobs", []):
        nodes[(module_name, "job", _local_name(module_name, job.name))] = job
    for page in program.pages:
        nodes[(module_name, "page", _local_name(module_name, page.name))] = page
    for ai in program.ais:
        nodes[(module_name, "ai", _local_name(module_name, ai.name))] = ai
    for tool in program.tools:
        nodes[(module_name, "tool", _local_name(module_name, tool.name))] = tool
    for agent in program.agents:
        nodes[(module_name, "agent", _local_name(module_name, agent.name))] = agent


def _local_name(module_name: str | None, name: str) -> str:
    if module_name and name.startswith(f"{module_name}."):
        return name.split(".", 1)[1]
    return name


def find_occurrence(
    index: ProjectIndex,
    file_path: Path,
    line: int,
    column: int,
) -> Tuple[SymbolDefinition | SymbolReference | None, str | None]:
    file_index = index.files.get(file_path)
    if not file_index:
        return None, None
    for definition in file_index.definitions:
        if definition.span.contains(line, column):
            return definition, "definition"
    for reference in file_index.references:
        if reference.span.contains(line, column):
            return reference, "reference"
    return None, None


def resolve_reference(
    index: ProjectIndex,
    file_path: Path,
    reference: SymbolReference,
) -> Tuple[str | None, str | None]:
    file_index = index.files.get(file_path)
    module_name = file_index.module if file_index else None
    raw = reference.raw_name
    if reference.kind == "capsule":
        return None, raw
    if "." in raw:
        prefix, name = raw.split(".", 1)
        alias_map = file_index.uses if file_index else {}
        if prefix in alias_map:
            return alias_map[prefix], name
        return None, None
    if (module_name, reference.kind, raw) in index.definitions:
        return module_name, raw
    return None, None


__all__ = ["build_index", "find_occurrence", "resolve_reference"]
