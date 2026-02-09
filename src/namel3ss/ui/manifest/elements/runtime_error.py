from __future__ import annotations

from typing import Any

from namel3ss.ui.manifest.canonical import _element_id


def inject_runtime_error_elements(manifest: dict, runtime_errors: list[dict[str, str]] | None) -> dict:
    if not isinstance(manifest, dict):
        return manifest
    pages = manifest.get("pages")
    if not isinstance(pages, list):
        return manifest
    normalized = _normalize_runtime_errors(runtime_errors)
    if not normalized:
        return manifest
    primary = normalized[0]
    diagnostics = normalized[1:]

    for page in pages:
        if not isinstance(page, dict):
            continue
        page_slug = str(page.get("slug") or page.get("name") or "page")
        page_name = str(page.get("name") or page_slug)
        element = _runtime_error_element(
            page_name=page_name,
            page_slug=page_slug,
            primary=primary,
            diagnostics=diagnostics,
        )
        if isinstance(page.get("layout"), dict):
            layout = page["layout"]
            main_items = layout.get("main")
            if not isinstance(main_items, list):
                main_items = []
            filtered = [entry for entry in main_items if not _is_runtime_error(entry)]
            layout["main"] = [element, *filtered]
            continue
        elements = page.get("elements")
        if not isinstance(elements, list):
            elements = []
            page["elements"] = elements
        filtered = [entry for entry in elements if not _is_runtime_error(entry)]
        page["elements"] = [element, *filtered]

    manifest["runtime_error"] = primary
    manifest["runtime_errors"] = normalized
    return manifest


def _runtime_error_element(
    *,
    page_name: str,
    page_slug: str,
    primary: dict[str, str],
    diagnostics: list[dict[str, str]],
) -> dict[str, Any]:
    element = {
        "type": "runtime_error",
        "element_id": _element_id(page_slug, "runtime_error", [0]),
        "page": page_name,
        "page_slug": page_slug,
        "index": 0,
        "line": 0,
        "column": 0,
        "category": primary["category"],
        "message": primary["message"],
        "hint": primary["hint"],
        "origin": primary["origin"],
        "stable_code": primary["stable_code"],
    }
    if diagnostics:
        element["diagnostics"] = diagnostics
    if primary["category"] in {"provider_misconfigured", "provider_mock_active"}:
        element["severity"] = "warn"
    else:
        element["severity"] = "error"
    return element


def _normalize_runtime_errors(value: object) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    ordered: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in value:
        entry = _normalize_runtime_error(item)
        if entry is None:
            continue
        stable_code = entry["stable_code"]
        if stable_code in seen:
            continue
        seen.add(stable_code)
        ordered.append(entry)
    return ordered


def _normalize_runtime_error(value: object) -> dict[str, str] | None:
    if not isinstance(value, dict):
        return None
    category = _as_text(value.get("category"))
    message = _as_text(value.get("message"))
    hint = _as_text(value.get("hint"))
    origin = _as_text(value.get("origin"))
    stable_code = _as_text(value.get("stable_code"))
    if not (category and message and hint and origin and stable_code):
        return None
    return {
        "category": category,
        "message": message,
        "hint": hint,
        "origin": origin,
        "stable_code": stable_code,
    }


def _is_runtime_error(entry: object) -> bool:
    return isinstance(entry, dict) and entry.get("type") == "runtime_error"


def _as_text(value: object) -> str:
    if isinstance(value, str):
        text = value.strip()
        return text
    return ""


__all__ = ["inject_runtime_error_elements"]
