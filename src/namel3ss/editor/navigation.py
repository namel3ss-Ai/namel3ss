from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from namel3ss.ast import nodes as ast
from namel3ss.editor.index import ProjectIndex, SymbolDefinition, SymbolReference, find_occurrence, resolve_reference
from namel3ss.editor.workspace import normalize_path


@dataclass(frozen=True)
class DefinitionLocation:
    file: str
    line: int
    column: int
    end_line: int
    end_column: int
    kind: str
    name: str

    def to_dict(self) -> dict:
        return {
            "file": self.file,
            "line": self.line,
            "column": self.column,
            "end_line": self.end_line,
            "end_column": self.end_column,
            "kind": self.kind,
            "name": self.name,
        }


def get_definition(index: ProjectIndex, *, file_path: Path, line: int, column: int) -> DefinitionLocation | None:
    occurrence, _ = find_occurrence(index, file_path, line, column)
    if occurrence is None:
        return None
    if isinstance(occurrence, SymbolDefinition):
        return _definition_location(index, occurrence)
    if isinstance(occurrence, SymbolReference):
        module_name, name = resolve_reference(index, file_path, occurrence)
        if name is None:
            return None
        key = (module_name, occurrence.kind, name)
        definition = index.definitions.get(key)
        if definition is None:
            return None
        return _definition_location(index, definition)
    return None


def get_hover(index: ProjectIndex, *, file_path: Path, line: int, column: int) -> str | None:
    occurrence, _ = find_occurrence(index, file_path, line, column)
    if occurrence is None:
        return None
    if isinstance(occurrence, SymbolDefinition):
        node = index.nodes.get((occurrence.module, occurrence.kind, occurrence.name))
        if node is None and occurrence.kind == "capsule":
            node = index.nodes.get((None, "capsule", occurrence.name))
        return _format_hover(occurrence, node)
    if isinstance(occurrence, SymbolReference):
        module_name, name = resolve_reference(index, file_path, occurrence)
        if name is None:
            return None
        node = index.nodes.get((module_name, occurrence.kind, name))
        definition = index.definitions.get((module_name, occurrence.kind, name))
        return _format_hover(definition, node)
    return None


def _definition_location(index: ProjectIndex, definition: SymbolDefinition) -> DefinitionLocation:
    span = definition.span
    return DefinitionLocation(
        file=normalize_path(definition.file, index.root),
        line=span.line,
        column=span.column,
        end_line=span.end_line,
        end_column=span.end_column,
        kind=definition.kind,
        name=definition.name,
    )


def _format_hover(definition: SymbolDefinition | None, node: ast.Node | None) -> str | None:
    if definition is None:
        return None
    label = f'{definition.kind} "{definition.name}"'
    if node is None:
        return label
    if isinstance(node, ast.RecordDecl):
        return _hover_record(definition, node)
    if isinstance(node, ast.Flow):
        requires = "yes" if node.requires is not None else "no"
        audited = "yes" if getattr(node, "audited", False) else "no"
        return f'{label} (requires: {requires}, audited: {audited})'
    if isinstance(node, ast.PageDecl):
        title = _page_title(node)
        requires = "yes" if node.requires is not None else "no"
        suffix = f" title: {title}" if title else ""
        return f'{label} (requires: {requires}){suffix}'
    if isinstance(node, ast.IdentityDecl):
        fields = ", ".join(field.name for field in node.fields[:3])
        more = "" if len(node.fields) <= 3 else f", +{len(node.fields) - 3} more"
        trust = f" trust_levels: {', '.join(node.trust_levels)}" if node.trust_levels else ""
        return f'{label} (fields: {fields}{more}){trust}'
    if isinstance(node, ast.CapsuleDecl):
        export_count = len(node.exports)
        return f'{label} (exports: {export_count})'
    if isinstance(node, ast.AIDecl):
        provider = node.provider or "default"
        return f'{label} (provider: {provider}, model: {node.model})'
    if isinstance(node, ast.ToolDecl):
        return f'{label} (kind: {node.kind})'
    if isinstance(node, ast.AgentDecl):
        return f'{label} (ai: {node.ai_name})'
    return label


def _hover_record(definition: SymbolDefinition, record: ast.RecordDecl) -> str:
    parts = []
    for field in record.fields[:3]:
        constraint = _constraint_summary(field.constraint)
        suffix = f" {constraint}" if constraint else ""
        parts.append(f"{field.name}: {field.type_name}{suffix}")
    more = "" if len(record.fields) <= 3 else f", +{len(record.fields) - 3} more"
    fields_text = ", ".join(parts) + more
    return f'record "{definition.name}" (fields: {fields_text})'


def _constraint_summary(constraint: ast.FieldConstraint | None) -> str:
    if constraint is None:
        return ""
    kind = constraint.kind
    if kind == "present":
        return "must be present"
    if kind == "unique":
        return "must be unique"
    if kind == "gt":
        return "must be greater than"
    if kind == "lt":
        return "must be less than"
    if kind == "len_min":
        return "len >= ..."
    if kind == "len_max":
        return "len <= ..."
    if kind == "pattern":
        return "pattern"
    return kind


def _page_title(page: ast.PageDecl) -> str | None:
    for item in page.items:
        if isinstance(item, ast.TitleItem):
            return item.value
        if hasattr(item, "children"):
            for child in getattr(item, "children", []) or []:
                if isinstance(child, ast.TitleItem):
                    return child.value
    return None


__all__ = ["DefinitionLocation", "get_definition", "get_hover"]
