from __future__ import annotations

import json

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir.ui.layout_ir import lower_layout_page
from namel3ss.parser.ui.layout_primitives import REQUIRED_CAPABILITY, parse_layout_page
from namel3ss.ui.manifest.layout_schema import build_layout_manifest, manifest_json


MINIMAL_SOURCE = """page dashboard:
  sidebar:
    text left_pane

  main:
    sticky bottom:
      form search_form:
        section search
"""


REALISTIC_SOURCE = """page chat_workspace:
  state:
    ui.selected_document
    ui.selected_citation
    ui.sources_drawer_open

  sidebar:
    scroll area:
      tabs document_tabs:
        dynamic tabs from state.ui.selected_document
        on click open_document
        selected item is state.ui.selected_document
        card documents:
          expandable
          text quarterly_review

  main:
    two_pane:
      primary:
        scroll area:
          form chat_thread:
            wizard
            section messages
            text assistant_messages
      secondary:
        sticky bottom:
          form composer:
            keyboard shortcut ctrl+enter
            on click send_message

  drawer right trigger citation_click:
    media source_preview:
      inline crop
      annotation
      selected item is state.ui.selected_citation
      on click open_sources
"""


def _build_manifest(source: str, *, capabilities: tuple[str, ...] = (REQUIRED_CAPABILITY,)) -> dict:
    page = parse_layout_page(source, capabilities=capabilities)
    page_ir = lower_layout_page(page)
    return build_layout_manifest(page_ir)


def _collect_layout_types(nodes: list[dict]) -> list[str]:
    kinds: list[str] = []

    def walk(entry: dict) -> None:
        kinds.append(str(entry.get("type")))
        for key in ("children", "primary", "secondary", "left", "center", "right"):
            value = entry.get(key)
            if isinstance(value, list):
                for child in value:
                    if isinstance(child, dict):
                        walk(child)

    for node in nodes:
        walk(node)
    return kinds


def test_minimal_example_parses_and_lowers() -> None:
    manifest = _build_manifest(MINIMAL_SOURCE)
    assert manifest["page"]["name"] == "dashboard"
    assert [node["type"] for node in manifest["layout"]] == ["layout.sidebar", "layout.main"]
    main = manifest["layout"][1]
    assert [child["type"] for child in main["children"]] == ["layout.sticky"]


def test_realistic_example_manifest_snapshot() -> None:
    manifest = _build_manifest(REALISTIC_SOURCE)
    assert [entry["path"] for entry in manifest["state"]] == [
        "ui.selected_document",
        "ui.selected_citation",
        "ui.sources_drawer_open",
    ]
    assert _collect_layout_types(manifest["layout"]) == [
        "layout.sidebar",
        "layout.scroll_area",
        "component.tabs",
        "component.card",
        "component.literal",
        "layout.main",
        "layout.two_pane",
        "layout.scroll_area",
        "component.form",
        "component.literal",
        "layout.sticky",
        "component.form",
        "layout.drawer",
        "component.media",
    ]
    assert [(action["event"], action["target"]) for action in manifest["actions"]] == [
        ("click", "open_document"),
        ("click", "send_message"),
        ("keyboard_shortcut", "ctrl+enter"),
        ("click", "open_sources"),
    ]


def test_determinism_reparse_is_identical() -> None:
    first = manifest_json(_build_manifest(REALISTIC_SOURCE), pretty=True)
    second = manifest_json(_build_manifest(REALISTIC_SOURCE), pretty=True)
    assert first == second


def test_stable_ids_repeat_for_same_source() -> None:
    first = _build_manifest(REALISTIC_SOURCE)
    second = _build_manifest(REALISTIC_SOURCE)
    first_ids = json.dumps(first, sort_keys=True)
    second_ids = json.dumps(second, sort_keys=True)
    assert first_ids == second_ids


def test_nested_sidebar_fails() -> None:
    source = """page bad:
  sidebar:
    sidebar:
      text nope
"""
    with pytest.raises(Namel3ssError) as err:
        _build_manifest(source)
    assert "Nested sidebar blocks are not allowed" in str(err.value)


def test_nested_drawer_cycle_fails() -> None:
    source = """page bad:
  main:
    drawer right trigger open_info:
      drawer left trigger open_info:
        text loop
"""
    with pytest.raises(Namel3ssError) as err:
        _build_manifest(source)
    assert "Drawer trigger cycle detected" in str(err.value)


def test_conflicting_sticky_positions_fail() -> None:
    source = """page bad:
  main:
    sticky bottom:
      text one
    sticky bottom:
      text two
"""
    with pytest.raises(Namel3ssError) as err:
        _build_manifest(source)
    assert "Conflicting sticky position" in str(err.value)


def test_missing_drawer_trigger_id_fails() -> None:
    source = """page bad:
  drawer right:
    text no_trigger
"""
    with pytest.raises(Namel3ssError) as err:
        _build_manifest(source)
    assert "Drawer blocks must declare trigger_id" in str(err.value)


def test_empty_container_fails() -> None:
    source = """page bad:
  main:
    scroll area:
"""
    with pytest.raises(Namel3ssError) as err:
        _build_manifest(source)
    assert "Scroll area blocks must include at least one child" in str(err.value)


def test_undefined_state_reference_fails() -> None:
    source = """page bad:
  main:
    form picker:
      selected item is state.ui.unknown
"""
    with pytest.raises(Namel3ssError) as err:
        _build_manifest(source)
    assert "Undefined state reference" in str(err.value)


def test_missing_capability_fails_when_not_in_studio_mode() -> None:
    with pytest.raises(Namel3ssError) as err:
        parse_layout_page(MINIMAL_SOURCE, capabilities=())
    assert REQUIRED_CAPABILITY in str(err.value)


def test_syntax_errors_include_line_and_column() -> None:
    source = """page broken
  main:
    text missing_colon
"""
    with pytest.raises(Namel3ssError) as err:
        parse_layout_page(source, capabilities=(REQUIRED_CAPABILITY,))
    text = str(err.value)
    assert "[line" in text
    assert "col" in text
