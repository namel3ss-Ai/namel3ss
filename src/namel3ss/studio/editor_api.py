from __future__ import annotations

import difflib
from pathlib import Path

from namel3ss.editor.diagnostics import diagnose
from namel3ss.editor.fixes import fix_for_diagnostic
from namel3ss.editor.index import build_index
from namel3ss.editor.patch_apply import apply_text_edits, write_patches
from namel3ss.editor.patches import TextEdit
from namel3ss.editor.rename import rename_symbol
from namel3ss.editor.workspace import EditorWorkspace, normalize_path
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message


def diagnose_payload(app_path: str, payload: dict | None = None) -> dict:
    workspace = _workspace_from_payload(app_path, payload or {})
    overrides = workspace.build_overrides((payload or {}).get("files"))
    diagnostics = diagnose(workspace, overrides=overrides)
    return {
        "schema_version": 1,
        "diagnostics": [
            _diagnostic_with_fix_hint(diag.to_dict()) for diag in diagnostics
        ],
    }


def fix_payload(app_path: str, payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise Namel3ssError(_payload_message("Fix request must be a JSON object."))
    workspace = _workspace_from_payload(app_path, payload)
    file_path = _parse_file(workspace, payload)
    diagnostic_id = str(payload.get("diagnostic_id") or "")
    if not diagnostic_id:
        raise Namel3ssError(_payload_message("diagnostic_id is required."))
    overrides = workspace.build_overrides(payload.get("files"))
    source = overrides.get(file_path) if overrides else None
    if source is None:
        source = file_path.read_text(encoding="utf-8")
    edits = fix_for_diagnostic(root=workspace.root, file_path=file_path, diagnostic_id=diagnostic_id, source=source)
    preview = _build_preview(workspace.root, edits)
    return {
        "schema_version": 1,
        "status": "ok",
        "edits": [edit.to_dict() for edit in edits],
        "preview": preview,
    }


def rename_payload(app_path: str, payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise Namel3ssError(_payload_message("Rename request must be a JSON object."))
    workspace = _workspace_from_payload(app_path, payload)
    file_path, line, column = _parse_position(workspace, payload)
    new_name = str(payload.get("new_name") or "")
    overrides = workspace.build_overrides(payload.get("files"))
    project = workspace.load(overrides)
    index = build_index(project)
    edits = rename_symbol(index, file_path=file_path, line=line, column=column, new_name=new_name)
    preview = _build_preview(workspace.root, edits)
    return {
        "schema_version": 1,
        "status": "ok",
        "edits": [edit.to_dict() for edit in edits],
        "preview": preview,
    }


def apply_payload(app_path: str, payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise Namel3ssError(_payload_message("Apply request must be a JSON object."))
    raw_edits = payload.get("edits")
    if not isinstance(raw_edits, list):
        raise Namel3ssError(_payload_message("edits must be a list."))
    edits = [_parse_edit(item) for item in raw_edits]
    workspace = _workspace_from_payload(app_path, payload)
    patches = apply_text_edits(workspace.root, edits)
    written = write_patches(patches)
    diagnostics = diagnose(workspace)
    return {
        "schema_version": 1,
        "status": "ok",
        "applied_files": [normalize_path(path, workspace.root) for path in written],
        "diagnostics": [_diagnostic_with_fix_hint(diag.to_dict()) for diag in diagnostics],
    }


def _build_preview(root: Path, edits: list[TextEdit]) -> list[dict]:
    if not edits:
        return []
    patches = apply_text_edits(root, edits)
    previews: list[dict] = []
    for patch in patches:
        rel = normalize_path(patch.path, root)
        diff_lines = difflib.unified_diff(
            patch.original.splitlines(),
            patch.updated.splitlines(),
            fromfile=rel,
            tofile=rel,
            lineterm="",
        )
        previews.append({"file": rel, "diff": "\n".join(diff_lines)})
    return previews


def _workspace_from_payload(app_path: str, payload: dict) -> EditorWorkspace:
    entry = payload.get("entry")
    if entry:
        entry_path = Path(str(entry))
        if not entry_path.is_absolute():
            entry_path = Path(app_path).parent / entry_path
        return EditorWorkspace.from_app_path(entry_path)
    return EditorWorkspace.from_app_path(Path(app_path))


def _parse_file(workspace: EditorWorkspace, payload: dict) -> Path:
    raw = payload.get("file")
    if not raw:
        raise Namel3ssError(_payload_message("file is required."))
    path = Path(str(raw))
    if not path.is_absolute():
        path = workspace.root / path
    return _safe_resolve(path, workspace.root)


def _parse_position(workspace: EditorWorkspace, payload: dict) -> tuple[Path, int, int]:
    file_path = _parse_file(workspace, payload)
    pos = payload.get("position") or {}
    try:
        line = int(pos.get("line", 0))
        column = int(pos.get("column", 0))
    except Exception as err:
        raise Namel3ssError(_payload_message(f"position must include line/column: {err}")) from err
    if line <= 0 or column <= 0:
        raise Namel3ssError(_payload_message("position.line and position.column must be positive."))
    return file_path, line, column


def _parse_edit(item: dict) -> TextEdit:
    if not isinstance(item, dict):
        raise Namel3ssError(_payload_message("Each edit must be an object."))
    file_path = str(item.get("file") or "").strip()
    if not file_path:
        raise Namel3ssError(_payload_message("edit.file is required."))
    start = item.get("start") or {}
    end = item.get("end") or {}
    return TextEdit(
        file=file_path,
        start_line=int(start.get("line", 0)),
        start_column=int(start.get("column", 0)),
        end_line=int(end.get("line", 0)),
        end_column=int(end.get("column", 0)),
        text=str(item.get("text") or ""),
    )


def _safe_resolve(path: Path, root: Path) -> Path:
    try:
        resolved = path.resolve()
    except Exception:
        resolved = path
    try:
        resolved.relative_to(root.resolve())
    except Exception as err:
        raise Namel3ssError(_payload_message(f"file is outside the project root: {err}")) from err
    return resolved


def _payload_message(message: str) -> str:
    return build_guidance_message(
        what=message,
        why="Studio editor requests require valid payload fields.",
        fix="Review the request and try again.",
        example='{"file":"app.ai"}',
    )


def _diagnostic_with_fix_hint(entry: dict) -> dict:
    entry = dict(entry)
    diag_id = str(entry.get("id") or "")
    entry["fix_available"] = _fix_available(diag_id)
    return entry


def _fix_available(diagnostic_id: str) -> bool:
    if diagnostic_id.startswith("governance.requires_flow_missing:"):
        return True
    if diagnostic_id.startswith("governance.requires_page_missing:"):
        return True
    if diagnostic_id.startswith("module.missing_export:"):
        return True
    if diagnostic_id.startswith("lint.") or diagnostic_id.startswith("N3LINT"):
        return True
    return False


__all__ = ["apply_payload", "diagnose_payload", "fix_payload", "rename_payload"]
