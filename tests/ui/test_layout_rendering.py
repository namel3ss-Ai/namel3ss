from __future__ import annotations

from pathlib import Path

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir.ui.layout_ir import lower_layout_page
from namel3ss.parser.ui.layout_primitives import REQUIRED_CAPABILITY, parse_layout_page
from namel3ss.ui.manifest.layout_builder import build_layout_manifest_document


SOURCE = """page chat_workspace:
  state:
    ui.selected_citation

  sidebar:
    scroll area:
      text documents

  main:
    two_pane:
      primary:
        text conversation
      secondary:
        sticky bottom:
          form composer:
            on click send_message
            keyboard shortcut ctrl+enter

  card citation_card:
    on click citation_click
    text citation row

  drawer right trigger citation_click:
    media sources:
      selected item is state.ui.selected_citation
"""


def _build_manifest(
    source: str,
    *,
    parse_capabilities: tuple[str, ...] = (REQUIRED_CAPABILITY,),
    build_capabilities: tuple[str, ...] = (REQUIRED_CAPABILITY,),
    parse_studio: bool = False,
    build_studio: bool = False,
) -> dict:
    page_ast = parse_layout_page(source, capabilities=parse_capabilities, studio_mode=parse_studio)
    page_ir = lower_layout_page(page_ast)
    return build_layout_manifest_document(page_ir, capabilities=build_capabilities, studio_mode=build_studio)


def _walk_elements(elements: list[dict]) -> list[dict]:
    collected: list[dict] = []
    queue = [entry for entry in elements if isinstance(entry, dict)]
    while queue:
        node = queue.pop(0)
        collected.append(node)
        for key in ("children", "primary", "secondary", "left", "center", "right"):
            children = node.get(key)
            if not isinstance(children, list):
                continue
            for child in children:
                if isinstance(child, dict):
                    queue.append(child)
    return collected


def test_layout_manifest_builder_wires_action_ids_and_layout_state() -> None:
    manifest = _build_manifest(SOURCE)
    page = manifest["pages"][0]
    actions = manifest["actions"]
    elements = _walk_elements(page["elements"])

    drawer = next(node for node in elements if node.get("type") == "layout.drawer")
    card = next(node for node in elements if node.get("type") == "component.card")
    form = next(node for node in elements if node.get("type") == "component.form")

    card_click_action_id = card["bindings"]["on_click"]
    assert isinstance(card_click_action_id, str)
    assert actions[card_click_action_id]["type"] == "layout.drawer.open"
    assert actions[card_click_action_id]["target"] == drawer["id"]

    form_click_action_id = form["bindings"]["on_click"]
    assert actions[form_click_action_id]["type"] == "layout.interaction"
    assert actions[form_click_action_id]["target"] == "send_message"

    shortcut_actions = [entry for entry in actions.values() if entry["type"] == "layout.shortcut"]
    assert len(shortcut_actions) == 1
    assert shortcut_actions[0]["shortcut"] == "ctrl+enter"
    assert shortcut_actions[0]["payload"].get("dispatch_action_id") == form_click_action_id

    assert manifest["layout_state"]["drawers"][drawer["id"]] is False
    sticky = next(node for node in elements if node.get("type") == "layout.sticky")
    assert manifest["layout_state"]["sticky"][sticky["id"]]["visible"] is True


def test_layout_manifest_document_is_deterministic() -> None:
    first = _build_manifest(SOURCE)
    second = _build_manifest(SOURCE)
    assert first == second


def test_layout_manifest_builder_rejects_missing_capability_in_runtime_mode() -> None:
    page_ast = parse_layout_page(SOURCE, capabilities=(REQUIRED_CAPABILITY,))
    page_ir = lower_layout_page(page_ast)
    with pytest.raises(Namel3ssError) as err:
        build_layout_manifest_document(page_ir, capabilities=(), studio_mode=False)
    assert REQUIRED_CAPABILITY in str(err.value)


def test_layout_manifest_builder_allows_studio_mode_without_capability() -> None:
    manifest = _build_manifest(
        SOURCE,
        parse_capabilities=(),
        build_capabilities=(),
        parse_studio=True,
        build_studio=True,
    )
    assert manifest["mode"] == "studio"
    assert manifest["pages"][0]["name"] == "chat_workspace"


def test_renderer_contract_includes_new_layout_nodes_and_action_hooks() -> None:
    renderer = Path("src/namel3ss/studio/web/ui_renderer.js").read_text(encoding="utf-8")
    for marker in [
        'el.type === "layout.main"',
        'el.type === "layout.scroll_area"',
        'el.type === "layout.two_pane"',
        'el.type === "layout.three_pane"',
        'el.type === "component.form"',
        'el.type === "component.chat_thread"',
        'el.type === "component.citation_panel"',
        'el.type === "component.document_library"',
        'el.type === "component.ingestion_progress"',
        'el.type === "component.explain_mode"',
        'actionType === "layout.shortcut"',
        'actionType === "layout.interaction"',
        'actionType === "component.chat.send"',
        'actionType === "component.citation.open"',
        'actionType === "component.document.select"',
        'actionType === "component.ingestion.retry"',
        "data-layout-drawer-id",
    ]:
        assert marker in renderer

    css = Path("src/namel3ss/studio/web/styles/layout_tokens.css").read_text(encoding="utf-8")
    for selector in [
        ".n3-layout-main",
        ".n3-layout-scroll-area",
        ".n3-layout-two-pane",
        ".n3-layout-three-pane",
        ".n3-component-form",
        ".n3-component-chat-thread",
        ".n3-component-citation-panel",
        ".n3-component-document-library",
        ".n3-component-ingestion-progress",
        ".n3-component-explain-mode",
        ".n3-interactive",
    ]:
        assert selector in css
