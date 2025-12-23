from __future__ import annotations

import re
from pathlib import Path
from typing import List

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.editor.index import ProjectIndex, SymbolDefinition, SymbolReference, find_occurrence, resolve_reference
from namel3ss.editor.patches import TextEdit
from namel3ss.editor.workspace import normalize_path


IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def rename_symbol(
    index: ProjectIndex,
    *,
    file_path: Path,
    line: int,
    column: int,
    new_name: str,
) -> list[TextEdit]:
    new_name = (new_name or "").strip()
    if not new_name:
        raise Namel3ssError(
            build_guidance_message(
                what="Rename is missing a new name.",
                why="Renames require the replacement name.",
                fix="Provide a non-empty name.",
                example='rename "Customer" to "Client"',
            )
        )
    occurrence, _ = find_occurrence(index, file_path, line, column)
    if occurrence is None:
        raise Namel3ssError(
            build_guidance_message(
                what="No symbol found at the cursor.",
                why="Rename only works on named symbols like records or flows.",
                fix="Place the cursor on a symbol name and retry.",
                example='flow "checkout":',
            )
        )
    definition = _resolve_definition(index, file_path, occurrence)
    if definition.origin == "package":
        raise Namel3ssError(
            build_guidance_message(
                what="Cannot rename symbols inside installed packages.",
                why="Package sources are read-only by default.",
                fix="Copy the symbol into a local module before renaming.",
                example='modules/local/capsule.ai',
            )
        )
    if (definition.module, definition.kind, new_name) in index.definitions and new_name != definition.name:
        raise Namel3ssError(
            build_guidance_message(
                what="Rename would create a duplicate symbol.",
                why="Symbols in the same scope must be unique.",
                fix="Pick a different name.",
                example=f'Rename to "{definition.name}_new"',
            )
        )
    if definition.kind == "capsule" and not _is_identifier(new_name):
        raise Namel3ssError(
            build_guidance_message(
                what="Capsule names must be identifiers.",
                why="Capsule folders use the same name as the capsule.",
                fix="Use letters, numbers, or underscores without spaces.",
                example="rename to inventory_v2",
            )
        )

    edits: List[TextEdit] = []
    requires_identifier = _requires_identifier(index, definition)
    if requires_identifier and not _is_identifier(new_name):
        raise Namel3ssError(
            build_guidance_message(
                what="New name is not a valid identifier.",
                why="Some references use identifier syntax (e.g. inv.Name).",
                fix="Use letters, numbers, or underscores without spaces.",
                example="rename to CustomerV2",
            )
        )

    target_key = (definition.module, definition.kind, definition.name)
    for file_index in index.files.values():
        if file_index.origin == "package":
            continue
        for defn in file_index.definitions:
            if (defn.module, defn.kind, defn.name) == target_key:
                edits.append(_edit_for_definition(defn, new_name, index))
        for ref in file_index.references:
            if ref.kind != definition.kind:
                continue
            module_name, name = resolve_reference(index, file_index.path, ref)
            if (module_name, ref.kind, name) != target_key:
                continue
            edits.append(_edit_for_reference(ref, new_name, index))
    return _dedupe_edits(edits)


def _resolve_definition(index: ProjectIndex, file_path: Path, occurrence: SymbolDefinition | SymbolReference) -> SymbolDefinition:
    if isinstance(occurrence, SymbolDefinition):
        return occurrence
    module_name, name = resolve_reference(index, file_path, occurrence)
    if name is None:
        raise Namel3ssError(
            build_guidance_message(
                what="Reference could not be resolved.",
                why="The symbol might be missing or require an alias.",
                fix="Fix the reference first, then retry rename.",
                example='use "inventory" as inv',
            )
        )
    definition = index.definitions.get((module_name, occurrence.kind, name))
    if definition is None:
        raise Namel3ssError(
            build_guidance_message(
                what="Definition not found for the selected symbol.",
                why="The symbol might be external or missing.",
                fix="Define the symbol in this project or choose a local symbol.",
                example='record "Order":',
            )
        )
    return definition


def _requires_identifier(index: ProjectIndex, definition: SymbolDefinition) -> bool:
    target_key = (definition.module, definition.kind, definition.name)
    for file_index in index.files.values():
        for ref in file_index.references:
            if ref.kind != definition.kind:
                continue
            module_name, name = resolve_reference(index, file_index.path, ref)
            if (module_name, ref.kind, name) == target_key and not ref.is_string:
                return True
    return False


def _edit_for_definition(definition: SymbolDefinition, new_name: str, index: ProjectIndex) -> TextEdit:
    span = definition.span
    return TextEdit(
        file=normalize_path(definition.file, index.root),
        start_line=span.line,
        start_column=span.column,
        end_line=span.end_line,
        end_column=span.end_column,
        text=f'"{new_name}"',
    )


def _edit_for_reference(reference: SymbolReference, new_name: str, index: ProjectIndex) -> TextEdit:
    span = reference.replace_span
    raw = reference.raw_name
    if reference.is_string:
        if "." in raw:
            prefix, _ = raw.split(".", 1)
            replacement = f"{prefix}.{new_name}"
        else:
            replacement = new_name
        text = f'"{replacement}"'
    else:
        text = new_name
    return TextEdit(
        file=normalize_path(reference.file, index.root),
        start_line=span.line,
        start_column=span.column,
        end_line=span.end_line,
        end_column=span.end_column,
        text=text,
    )


def _dedupe_edits(edits: List[TextEdit]) -> List[TextEdit]:
    seen = set()
    unique: List[TextEdit] = []
    for edit in edits:
        key = (edit.file, edit.start_line, edit.start_column, edit.end_line, edit.end_column, edit.text)
        if key in seen:
            continue
        seen.add(key)
        unique.append(edit)
    return unique


def _is_identifier(value: str) -> bool:
    return bool(IDENT_RE.match(value))


__all__ = ["rename_symbol"]
