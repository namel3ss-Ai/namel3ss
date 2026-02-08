from __future__ import annotations

import hashlib

from namel3ss.determinism import canonical_json_dumps
from namel3ss.ui.manifest import build_manifest
from tests.conftest import lower_ir_program


SOURCE = '''flow "launch":
  return "ok"

page "Chat":
  layout:
    main:
      title is "Chat"
      button "Run":
        calls flow "launch"
      button "Trace action" debug_only is "trace":
        calls flow "launch"
    diagnostics:
      section "Trace":
        text is "trace details"

page "Explain":
  diagnostics is true
  layout:
    main:
      title is "Explain"
      text is "internal details"
'''


def _element_labels(page: dict) -> set[str]:
    labels: set[str] = set()
    for element in page.get("elements", []):
        if isinstance(element, dict) and isinstance(element.get("label"), str):
            labels.add(element["label"])
    layout = page.get("layout")
    if isinstance(layout, dict):
        for values in layout.values():
            if not isinstance(values, list):
                continue
            for element in values:
                if isinstance(element, dict) and isinstance(element.get("label"), str):
                    labels.add(element["label"])
    return labels


def _hash(manifest: dict) -> str:
    payload = canonical_json_dumps(manifest, pretty=False, drop_run_keys=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def test_manifest_separates_and_filters_diagnostics_content():
    program = lower_ir_program(SOURCE)

    studio = build_manifest(program, state={}, display_mode="studio")
    production = build_manifest(program, state={}, display_mode="production")
    production_with_diagnostics = build_manifest(program, state={}, display_mode="production", diagnostics_enabled=True)

    studio_pages = {page["slug"]: page for page in studio["pages"]}
    production_pages = {page["slug"]: page for page in production["pages"]}
    diagnostics_pages = {page["slug"]: page for page in production_with_diagnostics["pages"]}

    assert "explain" in studio_pages
    assert "explain" not in production_pages
    assert "explain" in diagnostics_pages

    chat_studio = studio_pages["chat"]
    chat_production = production_pages["chat"]
    chat_diagnostics = diagnostics_pages["chat"]
    assert isinstance(chat_studio.get("diagnostics_blocks"), list)
    assert "diagnostics_blocks" not in chat_production
    assert isinstance(chat_diagnostics.get("diagnostics_blocks"), list)

    assert "Trace action" in _element_labels(chat_studio)
    assert "Trace action" not in _element_labels(chat_production)
    assert "Trace action" in _element_labels(chat_diagnostics)

    assert studio["diagnostics_enabled"] is True
    assert production["diagnostics_enabled"] is False
    assert production_with_diagnostics["diagnostics_enabled"] is True


def test_manifest_diagnostics_filter_is_deterministic():
    program = lower_ir_program(SOURCE)
    first = build_manifest(program, state={}, display_mode="production", diagnostics_enabled=True)
    second = build_manifest(program, state={}, display_mode="production", diagnostics_enabled=True)
    assert first == second
    assert _hash(first) == _hash(second)
