from __future__ import annotations


UI_EXPORT_VERSION = "1"


def build_ui_export(manifest: dict) -> dict:
    pages = manifest.get("pages") if isinstance(manifest, dict) else None
    theme = manifest.get("theme") if isinstance(manifest, dict) else None
    ui_meta = manifest.get("ui") if isinstance(manifest, dict) else None
    return {
        "schema_version": UI_EXPORT_VERSION,
        "pages": [_export_page(page) for page in pages or []],
        "theme": theme or {},
        "ui": ui_meta or {},
    }


def _export_page(page: dict) -> dict:
    elements = page.get("elements") if isinstance(page, dict) else None
    return {
        "name": page.get("name") if isinstance(page, dict) else None,
        "slug": page.get("slug") if isinstance(page, dict) else None,
        "elements": [_export_element(element) for element in elements or []],
    }


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
    if exported.get("type") == "memory":
        exported.pop("items", None)
    if exported.get("type") == "thinking":
        exported.pop("active", None)
    if exported.get("type") == "tabs":
        exported.pop("active", None)
    if exported.get("type") in {"modal", "drawer"}:
        exported.pop("open", None)
    children = exported.get("children")
    if isinstance(children, list):
        exported["children"] = [_export_element(child) for child in children]
    return exported


__all__ = ["UI_EXPORT_VERSION", "build_ui_export"]
