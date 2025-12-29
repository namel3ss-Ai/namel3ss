from __future__ import annotations

from pathlib import Path

from namel3ss.editor.index import build_index
from namel3ss.editor.navigation import get_definition, get_hover
from namel3ss.editor.workspace import EditorWorkspace


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _make_project(tmp_path: Path) -> Path:
    app = tmp_path / "app.ai"
    _write(
        app,
        'spec is "1.0"\n\n'
        'use "inventory" as inv\n'
        'use "payments" as pay\n'
        'page "home":\n'
        '  title is "Home"\n'
        '  form is inv.Product\n'
        '  button "Pay":\n'
        '    calls flow "pay.charge"\n',
    )
    _write(
        tmp_path / "modules" / "inventory" / "capsule.ai",
        'capsule "inventory":\n'
        "  exports:\n"
        '    record "Product"\n'
        '    flow "calc_total"\n',
    )
    _write(
        tmp_path / "modules" / "inventory" / "logic.ai",
        'record "Product":\n'
        "  name text\n\n"
        'flow "calc_total":\n'
        "  return 42\n",
    )
    _write(
        tmp_path / "packages" / "payments" / "capsule.ai",
        'capsule "payments":\n'
        "  exports:\n"
        '    flow "charge"\n',
    )
    _write(
        tmp_path / "packages" / "payments" / "logic.ai",
        'flow "charge":\n'
        '  return "ok"\n',
    )
    return app


def test_symbol_index_includes_modules_and_packages(tmp_path: Path) -> None:
    app = _make_project(tmp_path)
    workspace = EditorWorkspace.from_app_path(app)
    project = workspace.load()
    index = build_index(project)

    keys = {(d.kind, d.name, d.module, d.origin) for d in index.definitions.values()}
    assert ("record", "Product", "inventory", "module") in keys
    assert ("flow", "charge", "payments", "package") in keys

    product = next(d for d in index.definitions.values() if d.kind == "record" and d.name == "Product")
    assert product.exported is True


def test_definition_and_hover_across_modules(tmp_path: Path) -> None:
    app = _make_project(tmp_path)
    workspace = EditorWorkspace.from_app_path(app)
    project = workspace.load()
    index = build_index(project)

    lines = app.read_text(encoding="utf-8").splitlines()
    line_no = next(i for i, line in enumerate(lines, start=1) if "inv.Product" in line)
    column = lines[line_no - 1].index("inv.Product") + 1

    definition = get_definition(index, file_path=app, line=line_no, column=column)
    assert definition is not None
    assert definition.file.endswith("modules/inventory/logic.ai")

    hover = get_hover(index, file_path=app, line=line_no, column=column)
    assert hover is not None
    assert 'record "Product"' in hover
