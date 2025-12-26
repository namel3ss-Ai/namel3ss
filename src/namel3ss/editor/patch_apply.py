from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from namel3ss.editor.patches import TextEdit
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message


@dataclass(frozen=True)
class FilePatch:
    path: Path
    original: str
    updated: str


def apply_text_edits(root: Path, edits: list[TextEdit]) -> list[FilePatch]:
    grouped: dict[Path, list[TextEdit]] = {}
    for edit in edits:
        path = _resolve_path(root, edit.file)
        grouped.setdefault(path, []).append(edit)
    patches: list[FilePatch] = []
    for path, file_edits in grouped.items():
        original = path.read_text(encoding="utf-8")
        updated = _apply_to_text(original, file_edits)
        patches.append(FilePatch(path=path, original=original, updated=updated))
    return patches


def write_patches(patches: list[FilePatch]) -> list[Path]:
    written: list[Path] = []
    for patch in patches:
        patch.path.parent.mkdir(parents=True, exist_ok=True)
        patch.path.write_text(patch.updated, encoding="utf-8")
        written.append(patch.path)
    return written


def _apply_to_text(source: str, edits: list[TextEdit]) -> str:
    lines = source.splitlines(keepends=True)
    sorted_edits = sorted(
        edits,
        key=lambda e: (e.start_line, e.start_column, e.end_line, e.end_column),
        reverse=True,
    )
    updated = source
    for edit in sorted_edits:
        start = _offset(lines, edit.start_line, edit.start_column)
        end = _offset(lines, edit.end_line, edit.end_column)
        if end < start:
            raise Namel3ssError(_invalid_edit_message(edit))
        updated = updated[:start] + edit.text + updated[end:]
        lines = updated.splitlines(keepends=True)
    return updated


def _offset(lines: list[str], line: int, column: int) -> int:
    if line <= 0 or column <= 0:
        raise Namel3ssError(_position_message(line, column))
    if line > len(lines):
        raise Namel3ssError(_position_message(line, column))
    prefix = "".join(lines[: line - 1])
    line_text = lines[line - 1]
    line_body = line_text.rstrip("\n")
    line_body = line_body.rstrip("\r")
    max_col = len(line_body) + 1
    if column > max_col:
        raise Namel3ssError(_position_message(line, column))
    return len(prefix) + (column - 1)


def _resolve_path(root: Path, raw: str) -> Path:
    path = Path(raw)
    if not path.is_absolute():
        path = root / path
    try:
        resolved = path.resolve()
    except Exception:
        resolved = path
    try:
        resolved.relative_to(root.resolve())
    except Exception as err:
        raise Namel3ssError(
            build_guidance_message(
                what="Patch path is outside the project root.",
                why=str(err),
                fix="Use a path inside the project directory.",
                example="app.ai",
            )
        ) from err
    return resolved


def _position_message(line: int, column: int) -> str:
    return build_guidance_message(
        what="Patch position is invalid.",
        why=f"Line {line}, column {column} is outside the file.",
        fix="Refresh diagnostics and retry.",
        example="n3 editor",
    )


def _invalid_edit_message(edit: TextEdit) -> str:
    return build_guidance_message(
        what="Patch edit range is invalid.",
        why=(
            f"Start ({edit.start_line}:{edit.start_column}) must be before "
            f"end ({edit.end_line}:{edit.end_column})."
        ),
        fix="Refresh diagnostics and retry.",
        example="n3 editor",
    )


__all__ = ["FilePatch", "apply_text_edits", "write_patches"]
