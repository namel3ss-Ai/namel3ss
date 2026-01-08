from __future__ import annotations

from typing import Dict

from namel3ss.ui.manifest.canonical import _slugify


def _button_action_id(page_name: str, label: str) -> str:
    return f"page.{_slugify(page_name)}.button.{_slugify(label)}"


def _form_action_id(page_name: str, record_name: str) -> str:
    return f"page.{_slugify(page_name)}.form.{_slugify(record_name)}"


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


__all__ = ["_button_action_id", "_form_action_id", "_wire_overlay_actions"]
