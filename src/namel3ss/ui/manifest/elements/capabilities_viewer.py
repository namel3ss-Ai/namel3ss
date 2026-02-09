from __future__ import annotations

from typing import Any

from namel3ss.ui.manifest.canonical import _element_id


def inject_capabilities_viewer_elements(
    manifest: dict,
    *,
    capabilities_enabled: object,
    capability_versions: object,
) -> dict:
    if not isinstance(manifest, dict):
        return manifest
    pages = manifest.get("pages")
    if not isinstance(pages, list):
        return manifest
    packs = _normalize_packs(capabilities_enabled)
    versions = _normalize_versions(capability_versions)
    if not packs and not versions:
        return manifest
    for page in pages:
        if not isinstance(page, dict):
            continue
        page_slug = str(page.get("slug") or page.get("name") or "page")
        page_name = str(page.get("name") or page_slug)
        element = _capabilities_element(
            page_name=page_name,
            page_slug=page_slug,
            packs=packs,
            versions=versions,
        )
        if isinstance(page.get("layout"), dict):
            layout = page["layout"]
            main_items = layout.get("main")
            if not isinstance(main_items, list):
                main_items = []
            layout["main"] = _inject_element(main_items, element)
            continue
        elements = page.get("elements")
        if not isinstance(elements, list):
            elements = []
            page["elements"] = elements
        page["elements"] = _inject_element(elements, element)
    manifest["capabilities_enabled"] = packs
    manifest["capability_versions"] = versions
    return manifest


def _inject_element(items: list[dict], element: dict[str, Any]) -> list[dict]:
    filtered = [entry for entry in items if not _is_capabilities_viewer(entry)]
    if filtered and isinstance(filtered[0], dict) and filtered[0].get("type") == "runtime_error":
        return [filtered[0], element, *filtered[1:]]
    return [element, *filtered]


def _capabilities_element(
    *,
    page_name: str,
    page_slug: str,
    packs: list[dict[str, object]],
    versions: dict[str, str],
) -> dict[str, Any]:
    return {
        "type": "capabilities",
        "element_id": _element_id(page_slug, "capabilities", [0]),
        "page": page_name,
        "page_slug": page_slug,
        "index": 0,
        "line": 0,
        "column": 0,
        "source": "runtime.capabilities",
        "capabilities_enabled": packs,
        "capability_versions": versions,
    }


def _normalize_packs(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    normalized: list[dict[str, object]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        name = _as_text(item.get("name"))
        version = _as_text(item.get("version"))
        if not name or not version:
            continue
        entry: dict[str, object] = {
            "name": name,
            "version": version,
            "provided_actions": _sorted_text_list(item.get("provided_actions")),
            "required_permissions": _sorted_text_list(item.get("required_permissions")),
            "runtime_bindings": _normalize_bindings(item.get("runtime_bindings")),
            "effect_capabilities": _sorted_text_list(item.get("effect_capabilities")),
            "contract_version": _as_text(item.get("contract_version")),
            "purity": _as_text(item.get("purity")),
            "replay_mode": _as_text(item.get("replay_mode")),
        }
        normalized.append(entry)
    normalized.sort(key=lambda item: (str(item.get("name") or ""), str(item.get("version") or "")))
    return normalized


def _normalize_versions(value: object) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    normalized: dict[str, str] = {}
    for key in sorted(value.keys(), key=str):
        key_text = _as_text(key)
        version_text = _as_text(value.get(key))
        if key_text and version_text:
            normalized[key_text] = version_text
    return normalized


def _normalize_bindings(value: object) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    bindings: dict[str, str] = {}
    for key in sorted(value.keys(), key=str):
        key_text = _as_text(key)
        value_text = _as_text(value.get(key))
        if key_text and value_text:
            bindings[key_text] = value_text
    return bindings


def _sorted_text_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    deduped: dict[str, None] = {}
    for item in value:
        text = _as_text(item)
        if text:
            deduped[text] = None
    return sorted(deduped)


def _as_text(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    return ""


def _is_capabilities_viewer(entry: object) -> bool:
    return isinstance(entry, dict) and entry.get("type") == "capabilities"


__all__ = ["inject_capabilities_viewer_elements"]
