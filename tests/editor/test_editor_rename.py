from __future__ import annotations

from pathlib import Path

from namel3ss.editor.index import build_index
from namel3ss.editor.rename import rename_symbol
from namel3ss.editor.workspace import EditorWorkspace


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _make_project(tmp_path: Path) -> tuple[Path, Path, Path]:
    app = tmp_path / "app.ai"
    _write(
        app,
        'spec is "1.0"\n\n'
        'use "inventory" as inv\n'
        'page "home":\n'
        '  title is "Home"\n'
        '  form is inv.Product\n',
    )
    capsule = tmp_path / "modules" / "inventory" / "capsule.ai"
    _write(
        capsule,
        'capsule "inventory":\n'
        "  exports:\n"
        '    record "Product"\n',
    )
    logic = tmp_path / "modules" / "inventory" / "logic.ai"
    _write(
        logic,
        'record "Product":\n'
        "  name text\n",
    )
    return app, capsule, logic


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


def test_rename_record_updates_references(tmp_path: Path) -> None:
    app, capsule, logic = _make_project(tmp_path)
    workspace = EditorWorkspace.from_app_path(app)
    project = workspace.load()
    index = build_index(project)

    lines = app.read_text(encoding="utf-8").splitlines()
    line_no = next(i for i, line in enumerate(lines, start=1) if "inv.Product" in line)
    column = lines[line_no - 1].index("Product") + 1

    edits = rename_symbol(index, file_path=app, line=line_no, column=column, new_name="Item")

    app_text = _apply_edits(app.read_text(encoding="utf-8"), [e for e in edits if e.file.endswith("app.ai")])
    cap_text = _apply_edits(capsule.read_text(encoding="utf-8"), [e for e in edits if e.file.endswith("capsule.ai")])
    logic_text = _apply_edits(logic.read_text(encoding="utf-8"), [e for e in edits if e.file.endswith("logic.ai")])

    assert 'form is inv.Item' in app_text
    assert 'record "Item"' in cap_text
    assert 'record "Item"' in logic_text
