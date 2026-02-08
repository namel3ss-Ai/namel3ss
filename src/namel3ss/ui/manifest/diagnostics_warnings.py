from __future__ import annotations

from namel3ss.ui.manifest.page_structure import page_root_elements, walk_elements
from namel3ss.validation import add_warning

_IMPLICIT_DEBUG_TYPES = {"thinking", "memory"}


def append_diagnostics_warnings(pages: list[dict], warnings: list | None, context: dict | None = None) -> None:
    del context
    if warnings is None:
        return
    findings: list[dict] = []
    for page in pages:
        if not isinstance(page, dict):
            continue
        if bool(page.get("diagnostics")):
            continue
        page_slug = str(page.get("slug") or page.get("name") or "page")
        has_diagnostics_block = isinstance(page.get("diagnostics_blocks"), list) and bool(page.get("diagnostics_blocks"))
        for element in walk_elements(page_root_elements(page)):
            if not _should_warn(element):
                continue
            findings.append(
                {
                    "page_slug": page_slug,
                    "path": element.get("element_id") or f"page.{page_slug}",
                    "line": element.get("line"),
                    "column": element.get("column"),
                    "has_diagnostics_block": has_diagnostics_block,
                }
            )
    findings.sort(key=_sort_key)
    for finding in findings:
        fix = "Move diagnostics content into `layout: diagnostics:`." if finding["has_diagnostics_block"] else "Add a `layout: diagnostics:` block for diagnostics content."
        add_warning(
            warnings,
            code="diagnostics.misplaced_debug_content",
            message="Diagnostics-oriented UI content is mixed into the product layout.",
            fix=fix,
            path=finding["path"],
            line=finding["line"],
            column=finding["column"],
            category="diagnostics",
        )


def _sort_key(finding: dict) -> tuple[str, int, int]:
    return (
        str(finding.get("path") or ""),
        int(finding.get("line") or 0),
        int(finding.get("column") or 0),
    )


def _should_warn(element: dict) -> bool:
    debug_only = element.get("debug_only")
    if debug_only is not None and debug_only is not False:
        return True
    element_type = element.get("type")
    if not isinstance(element_type, str):
        return False
    if element_type not in _IMPLICIT_DEBUG_TYPES:
        return False
    return "debug_only" not in element or element.get("debug_only") is not False


__all__ = ["append_diagnostics_warnings"]
