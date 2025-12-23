from __future__ import annotations

import re
from pathlib import Path
from typing import List

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.format.formatter import format_source
from namel3ss.editor.patches import TextEdit
from namel3ss.editor.workspace import normalize_path


REQUIRES_FLOW_PREFIX = "governance.requires_flow_missing:"
REQUIRES_PAGE_PREFIX = "governance.requires_page_missing:"
MISSING_EXPORT_PREFIX = "module.missing_export:"


def fix_for_diagnostic(
    *,
    root: Path,
    file_path: Path,
    diagnostic_id: str,
    source: str,
) -> list[TextEdit]:
    if diagnostic_id.startswith(REQUIRES_FLOW_PREFIX):
        name = diagnostic_id[len(REQUIRES_FLOW_PREFIX) :]
        return _add_requires(root, file_path, source, kind="flow", name=name)
    if diagnostic_id.startswith(REQUIRES_PAGE_PREFIX):
        name = diagnostic_id[len(REQUIRES_PAGE_PREFIX) :]
        return _add_requires(root, file_path, source, kind="page", name=name)
    if diagnostic_id.startswith(MISSING_EXPORT_PREFIX):
        parts = diagnostic_id[len(MISSING_EXPORT_PREFIX) :].split(":")
        if len(parts) != 3:
            raise _fix_error("Diagnostic id is missing export details.")
        module_name, kind, symbol = parts
        return _add_export(root, module_name, kind, symbol)
    if diagnostic_id.startswith("lint.") or diagnostic_id.startswith("N3LINT"):
        return _format_file(root, file_path, source)
    raise _fix_error("No fix is available for this diagnostic.")


def _add_requires(
    root: Path,
    file_path: Path,
    source: str,
    *,
    kind: str,
    name: str,
) -> list[TextEdit]:
    pattern = re.compile(rf'^(?P<indent>\s*){kind}\s+"{re.escape(name)}"\s*:(?P<rest>.*)$')
    lines = source.splitlines()
    for i, line in enumerate(lines, start=1):
        match = pattern.match(line)
        if not match:
            continue
        rest = match.group("rest")
        if "requires" in rest:
            return []
        insert = ' requires identity.role is "admin"'
        if kind == "flow" and "audited" in rest:
            audited_idx = rest.find("audited")
            before = rest[:audited_idx].rstrip()
            after = rest[audited_idx:].lstrip()
            rest = f"{before}{insert} {after}".rstrip()
        else:
            rest = f"{rest}{insert}"
        colon_idx = match.start("rest") - 1
        new_line = f"{line[:colon_idx]}:{rest}"
        return [
            TextEdit(
                file=normalize_path(file_path, root),
                start_line=i,
                start_column=1,
                end_line=i,
                end_column=len(line) + 1,
                text=new_line,
            )
        ]
    raise _fix_error(f'Could not find {kind} "{name}" header.')


def _add_export(root: Path, module_name: str, kind: str, symbol: str) -> list[TextEdit]:
    capsule_path = _capsule_path(root, module_name)
    if capsule_path is None:
        raise _fix_error("Capsule file not found for export fix.")
    source = capsule_path.read_text(encoding="utf-8")
    if f'{kind} "{symbol}"' in source:
        return []
    lines = source.splitlines()
    exports_line = None
    exports_indent = ""
    for idx, line in enumerate(lines):
        if line.strip() == "exports:":
            exports_line = idx
            exports_indent = line[: len(line) - len(line.lstrip())]
            break
    if exports_line is None:
        raise _fix_error("Capsule exports block not found.")
    entry_indent = exports_indent + "  "
    insert_line = f'{entry_indent}{kind} "{symbol}"'
    insert_at = exports_line + 1
    while insert_at < len(lines):
        current = lines[insert_at]
        if current.strip() == "":
            insert_at += 1
            continue
        current_indent = len(current) - len(current.lstrip())
        if current_indent <= len(exports_indent):
            break
        insert_at += 1
    lines.insert(insert_at, insert_line)
    updated = "\n".join(lines)
    if source.endswith("\n"):
        updated += "\n"
    return [_replace_entire_file(root, capsule_path, source, updated)]


def _format_file(root: Path, file_path: Path, source: str) -> list[TextEdit]:
    formatted = format_source(source)
    if formatted == source:
        return []
    return [_replace_entire_file(root, file_path, source, formatted)]


def _replace_entire_file(root: Path, file_path: Path, original: str, updated: str) -> TextEdit:
    lines = original.splitlines() or [""]
    end_line = len(lines)
    end_column = len(lines[-1]) + 1
    return TextEdit(
        file=normalize_path(file_path, root),
        start_line=1,
        start_column=1,
        end_line=end_line,
        end_column=end_column,
        text=updated,
    )


def _capsule_path(root: Path, module_name: str) -> Path | None:
    candidate = root / "modules" / module_name / "capsule.ai"
    return candidate if candidate.exists() else None


def _fix_error(message: str) -> Namel3ssError:
    return Namel3ssError(
        build_guidance_message(
            what=message,
            why="The editor could not build a safe fix.",
            fix="Apply a manual edit or adjust the request.",
            example='n3 editor',
        )
    )


__all__ = ["fix_for_diagnostic"]
