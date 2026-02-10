from __future__ import annotations

from typing import Dict

from namel3ss.ui.manifest.canonical import _slugify


def _button_action_id(page_slug: str, label: str) -> str:
    return f"page.{page_slug}.button.{_slugify(label)}"


def _form_action_id(page_slug: str, record_name: str) -> str:
    return f"page.{page_slug}.form.{_slugify(record_name)}"


def _link_action_id(page_slug: str, label: str) -> str:
    return f"page.{page_slug}.link.{_slugify(label)}"


def _input_action_id(page_slug: str, name: str) -> str:
    return f"page.{page_slug}.input.{_slugify(name)}"


def _upload_action_id(page_slug: str, name: str) -> str:
    return f"page.{page_slug}.upload.{_slugify(name)}"


def _upload_clear_action_id(page_slug: str, name: str) -> str:
    return f"page.{page_slug}.upload.{_slugify(name)}.clear"


def _ingestion_action_id(page_slug: str, name: str) -> str:
    return f"page.{page_slug}.upload.{_slugify(name)}.ingestion"


def _retrieval_action_id() -> str:
    return "app.retrieval"


def _ingestion_review_action_id() -> str:
    return "app.ingestion.review"


def _ingestion_skip_action_id() -> str:
    return "app.ingestion.skip"


def _upload_replace_action_id() -> str:
    return "app.upload.replace"


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


LAYOUT_ACTION_TYPES = (
    "layout.drawer.open",
    "layout.drawer.close",
    "layout.drawer.toggle",
    "layout.sticky.show",
    "layout.sticky.hide",
    "layout.sticky.toggle",
    "layout.selection.set",
    "layout.shortcut",
    "layout.interaction",
)


def build_layout_action_entry(
    *,
    action_id: str,
    action_type: str,
    target: str | None = None,
    event: str | None = None,
    node_id: str | None = None,
    payload: dict | None = None,
    line: int | None = None,
    column: int | None = None,
    order: int = 0,
    shortcut: str | None = None,
) -> dict:
    entry = {
        "id": action_id,
        "type": action_type,
        "target": target,
        "event": event,
        "node_id": node_id,
        "payload": payload or {},
        "line": line,
        "column": column,
        "order": int(order),
    }
    if shortcut:
        entry["shortcut"] = shortcut
    return entry


def normalize_action_entry(action_id: str, action: dict) -> dict:
    normalized = dict(action)
    normalized["id"] = str(normalized.get("id") or action_id)
    normalized["type"] = str(normalized.get("type") or "call_flow")
    target = normalized.get("target")
    normalized["target"] = str(target) if isinstance(target, str) else target
    event = normalized.get("event")
    normalized["event"] = str(event) if isinstance(event, str) else event
    node_id = normalized.get("node_id")
    normalized["node_id"] = str(node_id) if isinstance(node_id, str) else node_id
    payload = normalized.get("payload")
    normalized["payload"] = dict(payload) if isinstance(payload, dict) else {}
    line = normalized.get("line")
    column = normalized.get("column")
    order = normalized.get("order")
    normalized["line"] = int(line) if isinstance(line, int) else None
    normalized["column"] = int(column) if isinstance(column, int) else None
    normalized["order"] = int(order) if isinstance(order, int) else 0
    shortcut = normalized.get("shortcut")
    if isinstance(shortcut, str):
        normalized["shortcut"] = shortcut
    elif "shortcut" in normalized:
        normalized.pop("shortcut", None)
    return normalized


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


__all__ = [
    "_button_action_id",
    "_form_action_id",
    "_input_action_id",
    "_link_action_id",
    "_upload_action_id",
    "_upload_clear_action_id",
    "_ingestion_action_id",
    "_retrieval_action_id",
    "_ingestion_review_action_id",
    "_ingestion_skip_action_id",
    "_upload_replace_action_id",
    "_wire_overlay_actions",
    "_allocate_action_id",
    "LAYOUT_ACTION_TYPES",
    "build_layout_action_entry",
    "normalize_action_entry",
]
