from __future__ import annotations

import os
from pathlib import Path

from namel3ss.editor.diagnostics import diagnose
from namel3ss.editor.fixes import fix_for_diagnostic
from namel3ss.editor.workspace import EditorWorkspace


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _apply_edits(text: str, edits) -> str:
    lines = text.splitlines(keepends=True)

    def offset_at(line: int, column: int) -> int:
        return sum(len(l) for l in lines[: line - 1]) + (column - 1)

    replacements = []
    for edit in edits:
        start = offset_at(edit.start_line, edit.start_column)
        end = offset_at(edit.end_line, edit.end_column)
        replacements.append((start, end, edit.text))
    for start, end, replacement in sorted(replacements, reverse=True):
        text = text[:start] + replacement + text[end:]
    return text


def test_missing_export_fix(tmp_path: Path) -> None:
    app = tmp_path / "app.ai"
    _write(
        app,
        'use "inventory" as inv\n'
        'page "home":\n'
        '  button "Run":\n'
        '    calls flow "inv.internal"\n',
    )
    capsule = tmp_path / "modules" / "inventory" / "capsule.ai"
    _write(
        capsule,
        'capsule "inventory":\n'
        "  exports:\n"
        '    flow "public"\n',
    )
    _write(
        tmp_path / "modules" / "inventory" / "logic.ai",
        'flow "public":\n'
        "  return 1\n\n"
        'flow "internal":\n'
        "  return 2\n",
    )
    workspace = EditorWorkspace.from_app_path(app)
    diagnostics = diagnose(workspace)
    missing = next(d for d in diagnostics if d.id.startswith("module.missing_export"))
    edits = fix_for_diagnostic(
        root=workspace.root,
        file_path=app,
        diagnostic_id=missing.id,
        source=app.read_text(encoding="utf-8"),
    )
    updated = _apply_edits(capsule.read_text(encoding="utf-8"), edits)
    assert 'flow "internal"' in updated


def test_requires_fix(tmp_path: Path) -> None:
    app = tmp_path / "app.ai"
    _write(
        app,
        'record "Order":\n'
        "  id text\n\n"
        'flow "save_order":\n'
        '  create "Order" with state.order as order\n'
        "  return order\n",
    )
    workspace = EditorWorkspace.from_app_path(app)
    diagnostics = diagnose(workspace)
    missing = next(d for d in diagnostics if d.id.startswith("governance.requires_flow_missing"))
    edits = fix_for_diagnostic(
        root=workspace.root,
        file_path=app,
        diagnostic_id=missing.id,
        source=app.read_text(encoding="utf-8"),
    )
    updated = _apply_edits(app.read_text(encoding="utf-8"), edits)
    assert 'flow "save_order": requires identity.role is "admin"' in updated


def test_diagnostics_do_not_leak_env(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "SUPERSECRET")
    app = tmp_path / "app.ai"
    _write(
        app,
        'ai "assistant":\n'
        '  provider is "openai"\n'
        '  model is "gpt-4.1"\n',
    )
    workspace = EditorWorkspace.from_app_path(app)
    diagnostics = diagnose(workspace)
    serialized = "\n".join(str(item.to_dict()) for item in diagnostics)
    assert "SUPERSECRET" not in serialized
