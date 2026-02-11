from __future__ import annotations

from namel3ss.validation import add_warning

_MISSING_ENHANCED_CITATIONS_MESSAGE = (
    "Warning: Enhanced citations are disabled (missing capability ui.citations_enhanced). "
    "Falling back to legacy citations UI."
)


def append_citation_capability_warning(pages: list[dict], warnings: list | None, context: dict | None = None) -> None:
    if warnings is None:
        return
    capabilities = set((context or {}).get("capabilities") or ())
    if "ui.citations_enhanced" in capabilities:
        return
    if not _uses_citations(pages):
        return
    add_warning(
        warnings,
        code="citations.enhanced_disabled",
        message=_MISSING_ENHANCED_CITATIONS_MESSAGE,
        fix="Add capability 'ui.citations_enhanced' to enable inline citation chips and snippet previews.",
        path="manifest.pages",
        line=0,
        column=0,
        category="citations",
    )


def _uses_citations(pages: list[dict]) -> bool:
    for page in pages:
        if not isinstance(page, dict):
            continue
        layout = page.get("layout")
        if isinstance(layout, dict):
            for slot in ("header", "sidebar_left", "main", "drawer_right", "footer", "diagnostics"):
                if _elements_use_citations(layout.get(slot)):
                    return True
        if _elements_use_citations(page.get("elements")):
            return True
        if _elements_use_citations(page.get("diagnostics_blocks")):
            return True
    return False


def _elements_use_citations(value: object) -> bool:
    if not isinstance(value, list):
        return False
    for element in value:
        if not isinstance(element, dict):
            continue
        element_type = element.get("type")
        if element_type == "citation_chips":
            return True
        for key in ("children", "then_children", "else_children", "sidebar", "main"):
            if _elements_use_citations(element.get(key)):
                return True
    return False


__all__ = ["append_citation_capability_warning"]
