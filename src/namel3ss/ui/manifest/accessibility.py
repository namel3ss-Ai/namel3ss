from __future__ import annotations

from typing import Iterable

from namel3ss.ui.fields import label_from_identifier


_FIELD_ROLE_MAP: dict[str, str] = {
    "text": "textbox",
    "string": "textbox",
    "str": "textbox",
    "number": "spinbutton",
    "int": "spinbutton",
    "integer": "spinbutton",
    "bool": "checkbox",
    "boolean": "checkbox",
    "json": "textbox",
    "map": "textbox",
    "list": "textbox",
}

_FOCUSABLE_ROLES: set[str] = {"button", "link", "textbox", "checkbox", "spinbutton", "tab"}


def apply_accessibility_contract(pages: list[dict]) -> None:
    for page in pages:
        elements = page.get("elements") or []
        _apply_elements(elements, tab_counter=0)


def _apply_elements(elements: list[dict], tab_counter: int) -> int:
    for element in elements:
        if not isinstance(element, dict):
            continue
        tab_counter = _apply_element(element, tab_counter)
    return tab_counter


def _apply_element(element: dict, tab_counter: int) -> int:
    kind = str(element.get("type") or "")
    visible = element.get("visible", True) is not False

    if kind == "tabs":
        return _apply_tabs(element, tab_counter, visible=visible)
    if kind in {"modal", "drawer"}:
        return _apply_overlay(element, tab_counter, visible=visible)
    if kind == "form":
        label = _label_from_record(element.get("record"))
        accessibility = {
            "role": "form",
            "label": label,
        }
        tab_counter = _attach_accessibility(element, accessibility, tab_counter, visible=visible, focusable=False)
        if not visible:
            return tab_counter
        tab_counter = _apply_form_fields(element, tab_counter)
        return tab_counter

    accessibility = _accessibility_for_element(element, kind)
    tab_counter = _attach_accessibility(element, accessibility, tab_counter, visible=visible)

    children = element.get("children")
    if isinstance(children, list) and children:
        tab_counter = _apply_elements(children, tab_counter)

    if kind == "card":
        tab_counter = _apply_action_entries(element.get("actions"), tab_counter, assign_tab_order=True)
    if kind == "list":
        tab_counter = _apply_action_entries(element.get("actions"), tab_counter, assign_tab_order=False)
    if kind == "table":
        tab_counter = _apply_action_entries(element.get("row_actions"), tab_counter, assign_tab_order=False)
    return tab_counter


def _apply_tabs(element: dict, tab_counter: int, *, visible: bool) -> int:
    tabs = [tab for tab in (element.get("children") or []) if isinstance(tab, dict)]
    visible_tabs = [tab for tab in tabs if tab.get("visible", True) is not False]
    active_label = element.get("active") or element.get("default")
    active_tab = _resolve_active_tab(visible_tabs, active_label)
    label = _tabs_label(active_tab, visible_tabs)
    accessibility = {
        "role": "tablist",
        "label": label,
        "focus": {"entry": "active_tab"},
        "keyboard": {"navigation": "arrow"},
    }
    tab_counter = _attach_accessibility(element, accessibility, tab_counter, visible=visible, focusable=False)
    for tab in tabs:
        tab_visible = tab.get("visible", True) is not False
        tab_accessibility = _accessibility_for_tab(tab)
        tab_counter = _attach_accessibility(tab, tab_accessibility, tab_counter, visible=tab_visible)
        if tab is active_tab and tab_visible:
            tab_counter = _apply_elements(tab.get("children") or [], tab_counter)
    return tab_counter


def _apply_overlay(element: dict, tab_counter: int, *, visible: bool) -> int:
    label = _normalize_label(element.get("label"))
    role = "dialog" if element.get("type") == "modal" else "complementary"
    accessibility = {
        "role": role,
        "label": label,
        "focus": {"entry": "overlay", "containment": True, "restoration": "opener"},
        "keyboard": {"dismissal": "escape"},
    }
    tab_counter = _attach_accessibility(element, accessibility, tab_counter, visible=visible, focusable=False)
    if not visible:
        return tab_counter
    if not element.get("open"):
        return tab_counter
    children = element.get("children")
    if isinstance(children, list) and children:
        tab_counter = _apply_elements(children, tab_counter)
    return tab_counter


def _apply_form_fields(element: dict, tab_counter: int) -> int:
    fields = element.get("fields") or []
    for field in fields:
        if not isinstance(field, dict):
            continue
        field_label = field.get("label") or label_from_identifier(str(field.get("name") or ""))
        if field_label:
            field["label"] = field_label
        role = _field_role(field.get("type"))
        accessibility = {"role": role, "label": field_label}
        tab_counter = _attach_accessibility(field, accessibility, tab_counter, visible=True)
    return tab_counter


def _accessibility_for_element(element: dict, kind: str) -> dict | None:
    if kind == "button":
        return _accessibility_with_label("button", element.get("label"))
    if kind == "link":
        return _accessibility_with_label("link", element.get("label"))
    if kind == "upload":
        return _accessibility_with_label("button", element.get("name"))
    if kind == "input":
        name = element.get("name")
        label = label_from_identifier(str(name)) if isinstance(name, str) else name
        return _accessibility_with_label("textbox", label)
    if kind == "composer":
        return _accessibility_with_label("textbox", element.get("flow"))
    if kind in {"table", "list"}:
        record = element.get("record")
        if record:
            return _accessibility_with_label(kind, _label_from_record(record))
        return _accessibility_with_label(kind, element.get("source"))
    if kind == "view":
        representation = element.get("representation") or ""
        role = "table" if representation == "table" else "list"
        return _accessibility_with_label(role, _label_from_record(element.get("record")))
    if kind == "tab":
        return _accessibility_with_label("tab", element.get("label"))
    return None


def _accessibility_for_tab(tab: dict) -> dict | None:
    return _accessibility_with_label("tab", tab.get("label"))


def _apply_action_entries(entries: Iterable[dict] | None, tab_counter: int, *, assign_tab_order: bool) -> int:
    if not entries:
        return tab_counter
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        label = entry.get("label")
        accessibility = _accessibility_with_label("button", label)
        tab_counter = _attach_accessibility(entry, accessibility, tab_counter, visible=True, focusable=assign_tab_order)
    return tab_counter


def _attach_accessibility(
    element: dict,
    accessibility: dict | None,
    tab_counter: int,
    *,
    visible: bool,
    focusable: bool = True,
) -> int:
    if not accessibility:
        return tab_counter
    element["accessibility"] = accessibility
    if not visible:
        return tab_counter
    if focusable and _is_focusable(accessibility):
        tab_counter += 1
        accessibility["tab_order"] = tab_counter
    return tab_counter


def _is_focusable(accessibility: dict) -> bool:
    role = accessibility.get("role")
    return role in _FOCUSABLE_ROLES


def _accessibility_with_label(role: str, label: object) -> dict | None:
    label_text = _normalize_label(label)
    if not role:
        return None
    return {"role": role, "label": label_text}


def _field_role(value: object) -> str:
    if isinstance(value, str):
        return _FIELD_ROLE_MAP.get(value.lower(), "textbox")
    return "textbox"


def _label_from_record(value: object) -> str:
    if isinstance(value, str) and value.strip():
        return label_from_identifier(value)
    return ""


def _normalize_label(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        text = value.strip()
        return text
    return str(value)


def _resolve_active_tab(tabs: list[dict], active_label: object) -> dict | None:
    target = _normalize_label(active_label)
    if target:
        for tab in tabs:
            if _normalize_label(tab.get("label")) == target:
                return tab
    return tabs[0] if tabs else None


def _tabs_label(active: dict | None, tabs: list[dict]) -> str:
    if active is not None:
        return _normalize_label(active.get("label"))
    if tabs:
        return _normalize_label(tabs[0].get("label"))
    return ""


__all__ = ["apply_accessibility_contract"]
