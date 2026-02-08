from __future__ import annotations

from pathlib import Path

from namel3ss.ui.manifest import build_manifest
from namel3ss.validation import ValidationMode
from tests.conftest import lower_ir_program


PAGE_VISIBILITY_SOURCE = '''spec is "1.0"

page "home": visible when state.show_home
  title is "Home"

page "fallback":
  title is "Fallback"
'''


HIDDEN_EMPTY_STATE_SOURCE = '''spec is "1.0"

page "home":
  list from state.items:
    item:
      primary is name
    empty_state: hidden
  table from state.rows:
    columns:
      include name
    empty_state: false
'''


UNGUARDED_COLLECTIONS_SOURCE = '''spec is "1.0"

page "home":
  list from state.items:
    item:
      primary is name
  table from state.rows:
    columns:
      include name
'''


GUARDED_COLLECTIONS_SOURCE = '''spec is "1.0"

page "home":
  section "Guard" visible when state.show:
    list from state.items:
      item:
        primary is name
  section "Guarded table" visible when state.show:
    table from state.rows:
      columns:
        include name
'''


def test_page_visible_when_excludes_hidden_page() -> None:
    program = lower_ir_program(PAGE_VISIBILITY_SOURCE)
    hidden = build_manifest(program, state={"show_home": False}, store=None)
    visible = build_manifest(program, state={"show_home": True}, store=None)

    assert [page["slug"] for page in hidden["pages"]] == ["fallback"]
    assert [page["slug"] for page in visible["pages"]] == ["home", "fallback"]


def test_hidden_empty_state_sets_visible_false_in_studio_and_omits_in_production() -> None:
    program = lower_ir_program(HIDDEN_EMPTY_STATE_SOURCE)
    state = {"items": [], "rows": []}

    studio = build_manifest(program, state=state, store=None, display_mode="studio")
    production = build_manifest(program, state=state, store=None, display_mode="production")

    studio_elements = studio["pages"][0]["elements"]
    assert [el["type"] for el in studio_elements] == ["list", "table"]
    assert all(el.get("visible") is False for el in studio_elements)
    assert all(el.get("empty_state", {}).get("state") == "hidden" for el in studio_elements)

    assert production["pages"][0]["elements"] == []


def test_hidden_empty_state_keeps_non_empty_collections_visible() -> None:
    program = lower_ir_program(HIDDEN_EMPTY_STATE_SOURCE)
    state = {
        "items": [{"name": "One"}],
        "rows": [{"name": "Alpha"}],
    }
    manifest = build_manifest(program, state=state, store=None, display_mode="studio")
    elements = manifest["pages"][0]["elements"]
    assert [el["type"] for el in elements] == ["list", "table"]
    assert all(el.get("visible") is not False for el in elements)


def test_warning_emitted_for_unguarded_collections_with_empty_state() -> None:
    program = lower_ir_program(UNGUARDED_COLLECTIONS_SOURCE)
    warnings: list = []
    build_manifest(
        program,
        state={"items": [], "rows": []},
        store=None,
        mode=ValidationMode.STATIC,
        warnings=warnings,
    )
    codes = [warning.code for warning in warnings if getattr(warning, "code", "").startswith("visibility.")]
    assert codes.count("visibility.missing_empty_state_guard") == 2


def test_warning_not_emitted_when_collection_is_guarded() -> None:
    program = lower_ir_program(GUARDED_COLLECTIONS_SOURCE)
    warnings: list = []
    build_manifest(
        program,
        state={"show": True, "items": [], "rows": []},
        store=None,
        mode=ValidationMode.STATIC,
        warnings=warnings,
    )
    codes = [warning.code for warning in warnings if getattr(warning, "code", "").startswith("visibility.")]
    assert not codes


def test_custom_component_visible_when_is_respected(monkeypatch, tmp_path: Path) -> None:
    plugin_root = tmp_path / "ui_plugins" / "mini"
    plugin_root.mkdir(parents=True)
    (plugin_root / "renderer.py").write_text(
        "def render(props, state):\n"
        "    return [{\"type\": \"text\", \"text\": \"plugin\"}]\n",
        encoding="utf-8",
    )
    (plugin_root / "plugin.json").write_text(
        "{\n"
        '  "name": "mini",\n'
        '  "module": "renderer.py",\n'
        '  "components": [{"name": "MiniWidget", "props": {}}]\n'
        "}\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("N3_UI_PLUGIN_DIRS", str(tmp_path / "ui_plugins"))
    source = '''spec is "1.0"

capabilities:
  custom_ui
  sandbox

use plugin "mini"

page "home":
  MiniWidget visible when state.show_widget
'''
    program = lower_ir_program(source)
    hidden = build_manifest(program, state={"show_widget": False}, store=None, display_mode="production")
    visible = build_manifest(program, state={"show_widget": True}, store=None, display_mode="production")
    assert hidden["pages"][0]["elements"] == []
    assert visible["pages"][0]["elements"][0]["type"] == "custom_component"
