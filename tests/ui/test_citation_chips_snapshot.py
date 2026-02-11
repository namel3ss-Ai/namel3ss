from __future__ import annotations

from namel3ss.ui.manifest import build_manifest
from tests.conftest import lower_ir_program


_SOURCE = '''
spec is "1.0"

page "home":
  citations from state.answer.citations
'''.lstrip()


_SOURCE_ENHANCED = '''
spec is "1.0"

capabilities:
  ui.citations_enhanced

page "home":
  citations from state.answer.citations
'''.lstrip()


_STATE = {
    "answer": {
        "citations": [
            {
                "title": "Policy A",
                "source_id": "doc-a",
                "snippet": "This snippet is intentionally long " * 30,
            },
            {
                "citation_id": "c2",
                "title": "Policy B",
                "url": "https://example.com/policy-b",
                "snippet": "Short snippet.",
            },
        ]
    }
}


def test_citation_chips_fallback_warning_and_snapshot_contract() -> None:
    program = lower_ir_program(_SOURCE)
    warnings: list = []
    manifest = build_manifest(program, state=_STATE, warnings=warnings)
    chips = _first_citation_chips(manifest)
    assert chips["enhanced"] is False
    assert [entry["citation_id"] for entry in chips["citations"]] == ["citation.1", "c2"]
    assert chips["citations"][0]["snippet"].endswith("...")
    assert len(chips["citations"][0]["snippet"]) <= 223
    warning = next(item for item in warnings if item.code == "citations.enhanced_disabled")
    assert warning.message == (
        "Warning: Enhanced citations are disabled (missing capability ui.citations_enhanced). "
        "Falling back to legacy citations UI."
    )


def test_citation_chips_enhanced_mode_is_deterministic() -> None:
    program = lower_ir_program(_SOURCE_ENHANCED)
    first = build_manifest(program, state=_STATE, warnings=[])
    second = build_manifest(program, state=_STATE, warnings=[])
    assert first == second
    chips = _first_citation_chips(first)
    assert chips["enhanced"] is True


def _first_citation_chips(manifest: dict) -> dict:
    for element in _walk_elements(manifest):
        if element.get("type") == "citation_chips":
            return element
    raise AssertionError("citation_chips element not found")


def _walk_elements(manifest: dict):
    pages = manifest.get("pages") if isinstance(manifest, dict) else None
    if not isinstance(pages, list):
        return
    for page in pages:
        if not isinstance(page, dict):
            continue
        layout = page.get("layout")
        if isinstance(layout, dict):
            for slot in ("header", "sidebar_left", "main", "drawer_right", "footer", "diagnostics"):
                yield from _walk_element_list(layout.get(slot))
        yield from _walk_element_list(page.get("elements"))
        yield from _walk_element_list(page.get("diagnostics_blocks"))


def _walk_element_list(elements: object):
    if not isinstance(elements, list):
        return
    for element in elements:
        if not isinstance(element, dict):
            continue
        yield element
        for key in ("children", "then_children", "else_children", "sidebar", "main"):
            yield from _walk_element_list(element.get(key))
