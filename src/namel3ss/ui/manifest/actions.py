from __future__ import annotations

from typing import Dict

from namel3ss.ui.manifest.canonical import _slugify


def _button_action_id(page_slug: str, label: str) -> str:
    return f"page.{page_slug}.button.{_slugify(label)}"


def _form_action_id(page_slug: str, record_name: str) -> str:
    return f"page.{page_slug}.form.{_slugify(record_name)}"


def _allocate_action_id(base_id: str, element_id: str, taken: set[str]) -> str:
    if base_id not in taken:
        return base_id
    fallback = f"{base_id}__{element_id}"
    if fallback not in taken:
        return fallback
    index = 1
    while True:
        candidate = f"{fallback}.{index}"
        if candidate not in taken:
            return candidate
        index += 1


def _wire_overlay_actions(elements: list[dict], actions: Dict[str, dict]) -> None:
    overlay_map: Dict[str, dict] = {}
    for element in _walk_elements(elements):
        if element.get("type") in {"modal", "drawer"}:
            overlay_id = element.get("id")
            if isinstance(overlay_id, str):
                overlay_map[overlay_id] = element
                element.setdefault("open_actions", [])
                element.setdefault("close_actions", [])
    for action_id, action in actions.items():
        action_type = action.get("type")
        if action_type not in {"open_modal", "close_modal", "open_drawer", "close_drawer"}:
            continue
        target = action.get("target")
        if not isinstance(target, str):
            continue
        overlay = overlay_map.get(target)
        if overlay is None:
            continue
        if action_type.startswith("open"):
            overlay["open_actions"].append(action_id)
        else:
            overlay["close_actions"].append(action_id)
    for overlay in overlay_map.values():
        overlay["open_actions"] = sorted(set(overlay.get("open_actions") or []))
        overlay["close_actions"] = sorted(set(overlay.get("close_actions") or []))


def _walk_elements(elements: list[dict]) -> list[dict]:
    collected: list[dict] = []
    for element in elements:
        collected.append(element)
        children = element.get("children")
        if isinstance(children, list) and children:
            collected.extend(_walk_elements(children))
    return collected


__all__ = ["_button_action_id", "_form_action_id", "_wire_overlay_actions", "_allocate_action_id"]
