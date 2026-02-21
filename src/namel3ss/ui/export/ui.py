from __future__ import annotations

from namel3ss.page_layout import PAGE_LAYOUT_SLOT_ORDER, normalize_page_layout_dict


UI_EXPORT_VERSION = "1"


def build_ui_export(manifest: dict) -> dict:
    pages = manifest.get("pages") if isinstance(manifest, dict) else None
    theme = manifest.get("theme") if isinstance(manifest, dict) else None
    ui_meta = manifest.get("ui") if isinstance(manifest, dict) else None
    payload = {
        "schema_version": UI_EXPORT_VERSION,
        "pages": [_export_page(page) for page in pages or []],
        "theme": theme or {},
        "ui": ui_meta or {},
    }
    diagnostics_enabled = manifest.get("diagnostics_enabled") if isinstance(manifest, dict) else None
    if isinstance(diagnostics_enabled, bool):
        payload["diagnostics_enabled"] = diagnostics_enabled
    return payload


def _export_page(page: dict) -> dict:
    exported = {
        "name": page.get("name") if isinstance(page, dict) else None,
        "slug": page.get("slug") if isinstance(page, dict) else None,
    }
    if isinstance(page, dict) and isinstance(page.get("diagnostics"), bool):
        exported["diagnostics"] = bool(page.get("diagnostics"))
    layout = page.get("layout") if isinstance(page, dict) else None
    if isinstance(layout, dict):
        normalized = normalize_page_layout_dict(layout)
        exported["layout"] = {
            slot_name: [_export_element(element) for element in normalized.get(slot_name, [])]
            for slot_name in PAGE_LAYOUT_SLOT_ORDER
        }
        layout_options = page.get("layout_options") if isinstance(page, dict) else None
        if isinstance(layout_options, dict):
            exported["layout_options"] = {
                key: value
                for key, value in layout_options.items()
                if isinstance(key, str) and isinstance(value, (str, bool))
            }
        diagnostics_blocks = page.get("diagnostics_blocks") if isinstance(page, dict) else None
        if isinstance(diagnostics_blocks, list):
            exported["diagnostics_blocks"] = [_export_element(element) for element in diagnostics_blocks]
        return exported
    elements = page.get("elements") if isinstance(page, dict) else None
    exported["elements"] = [_export_element(element) for element in elements or []]
    diagnostics_blocks = page.get("diagnostics_blocks") if isinstance(page, dict) else None
    if isinstance(diagnostics_blocks, list):
        exported["diagnostics_blocks"] = [_export_element(element) for element in diagnostics_blocks]
    return exported


def _export_element(element: dict) -> dict:
    exported = dict(element)
    if exported.get("type") == "table":
        exported.pop("rows", None)
    if exported.get("type") == "list":
        exported.pop("rows", None)
    if exported.get("type") == "chart":
        exported.pop("series", None)
        exported.pop("summary", None)
    if exported.get("type") == "messages":
        exported.pop("messages", None)
    if exported.get("type") == "citations":
        exported.pop("citations", None)
    if exported.get("type") == "citation_chips":
        exported.pop("citations", None)
    if exported.get("type") == "memory":
        exported.pop("items", None)
    if exported.get("type") == "thinking":
        exported.pop("active", None)
    if exported.get("type") == "source_preview":
        exported.pop("snippet", None)
    if exported.get("type") == "trust_indicator":
        exported.pop("value", None)
    if exported.get("type") == "scope_selector":
        exported.pop("options", None)
        exported.pop("active", None)
    if exported.get("type") == "upload":
        exported.pop("files", None)
    if exported.get("type") == "tabs":
        exported.pop("active", None)
    if exported.get("type") in {"modal", "drawer"}:
        exported.pop("open", None)
    children = exported.get("children")
    if isinstance(children, list):
        exported["children"] = [_export_element(child) for child in children]
    return exported


__all__ = ["UI_EXPORT_VERSION", "build_ui_export"]
