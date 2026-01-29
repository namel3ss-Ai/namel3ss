from __future__ import annotations

from pathlib import Path

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.ui.explain.build_core import build_ui_explain_pack
from namel3ss.ui.manifest import build_manifest
from namel3ss.validation import ValidationMode
from tests.conftest import lower_ir_program


FIXTURE_APP = Path("tests/fixtures/ui_accessibility_app.ai")

INTERACTIVE_TYPES = {
    "button",
    "link",
    "upload",
    "form",
    "table",
    "list",
    "tabs",
    "tab",
    "modal",
    "drawer",
}


def _walk_elements(elements: list[dict]) -> list[dict]:
    items: list[dict] = []
    for element in elements:
        items.append(element)
        children = element.get("children")
        if isinstance(children, list) and children:
            items.extend(_walk_elements(children))
    return items


def _elements_by_type(manifest: dict, element_type: str) -> list[dict]:
    found: list[dict] = []
    for page in manifest.get("pages") or []:
        for element in _walk_elements(page.get("elements") or []):
            if element.get("type") == element_type:
                found.append(element)
    return found


def test_accessibility_roles_and_labels_present():
    program = lower_ir_program(FIXTURE_APP.read_text(encoding="utf-8"))
    manifest = build_manifest(program, state={}, store=None)
    elements = []
    for page in manifest.get("pages") or []:
        elements.extend(_walk_elements(page.get("elements") or []))
    interactive = [el for el in elements if el.get("type") in INTERACTIVE_TYPES]
    assert interactive, "fixture must include interactive elements"
    for element in interactive:
        accessibility = element.get("accessibility") or {}
        assert accessibility.get("role"), f"missing role for {element.get('type')}"
        assert accessibility.get("label") is not None, f"missing label for {element.get('type')}"


def test_form_fields_have_deterministic_labels():
    program = lower_ir_program(FIXTURE_APP.read_text(encoding="utf-8"))
    manifest = build_manifest(program, state={}, store=None)
    forms = _elements_by_type(manifest, "form")
    assert forms, "fixture must include a form"
    fields = forms[0].get("fields") or []
    labels = [field.get("label") for field in fields]
    assert labels == ["Title", "Count", "Done"]
    for field in fields:
        accessibility = field.get("accessibility") or {}
        assert accessibility.get("role"), "form field missing role"
        assert accessibility.get("label"), "form field missing label"


def test_focus_and_keyboard_contracts_for_tabs_and_overlays():
    program = lower_ir_program(FIXTURE_APP.read_text(encoding="utf-8"))
    manifest = build_manifest(program, state={}, store=None)
    tabs = _elements_by_type(manifest, "tabs")[0]
    tabs_accessibility = tabs.get("accessibility") or {}
    assert tabs_accessibility.get("focus"), "tabs missing focus contract"
    assert tabs_accessibility.get("keyboard"), "tabs missing keyboard contract"

    modal = _elements_by_type(manifest, "modal")[0]
    modal_accessibility = modal.get("accessibility") or {}
    assert modal_accessibility.get("focus"), "modal missing focus contract"
    assert modal_accessibility.get("keyboard"), "modal missing keyboard contract"

    drawer = _elements_by_type(manifest, "drawer")[0]
    drawer_accessibility = drawer.get("accessibility") or {}
    assert drawer_accessibility.get("focus"), "drawer missing focus contract"
    assert drawer_accessibility.get("keyboard"), "drawer missing keyboard contract"


def test_contrast_validation_rejects_unsafe_pair():
    source = 'ui:\n  theme is "white"\n  accent color is "yellow"\npage "home":\n  title is "Hi"\n'
    program = lower_ir_program(source)
    with pytest.raises(Namel3ssError) as exc:
        build_manifest(program, state={}, store=None, mode=ValidationMode.STATIC)
    assert "contrast" in str(exc.value).lower()


def test_explain_includes_accessibility_metadata():
    root = Path(__file__).resolve().parents[2]
    app_path = root / FIXTURE_APP
    pack = build_ui_explain_pack(root, str(app_path))
    pages = pack.get("pages") or []
    element_kinds = []
    for page in pages:
        element_kinds.extend(page.get("elements") or [])
    tabs_entries = [el for el in element_kinds if el.get("kind") == "tabs"]
    assert tabs_entries, "explain pack missing tabs element"
    tabs_accessibility = tabs_entries[0].get("accessibility") or {}
    assert tabs_accessibility.get("role") == "tablist"
    assert tabs_accessibility.get("focus")
