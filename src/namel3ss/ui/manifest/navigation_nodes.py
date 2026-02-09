from __future__ import annotations

from copy import deepcopy

from namel3ss.ir import nodes as ir
from namel3ss.ui.manifest.navigation import select_active_page
from namel3ss.ui.manifest.state_defaults import StateContext, StateDefaults


def build_navigation(
    program: ir.Program,
    *,
    pages: list[dict],
    state_base: dict,
    app_defaults: dict,
) -> dict | None:
    if not _navigation_feature_enabled(program):
        return None
    if not pages:
        return None
    page_entries = [
        {"name": str(page.get("name") or ""), "slug": str(page.get("slug") or "")}
        for page in pages
        if isinstance(page, dict) and page.get("name") and page.get("slug")
    ]
    if not page_entries:
        return None
    navigation_state = StateContext(deepcopy(state_base), StateDefaults(app_defaults))
    active_payload = select_active_page(
        getattr(program, "ui_active_page_rules", None),
        pages=pages,
        state_ctx=navigation_state,
    )
    active_info = (active_payload or {}).get("active_page") if isinstance(active_payload, dict) else None
    active_slug = _active_slug(active_info, page_entries)
    active_name = _active_name(active_info, active_slug, page_entries)
    sidebar_items = _build_sidebar_items(program, page_entries, active_slug, active_name)
    navigation: dict = {
        "pages": page_entries,
        "active": active_slug,
        "active_page": {
            "name": active_name,
            "slug": active_slug,
            "source": (active_info or {}).get("source", "default"),
        },
        "history": {"enabled": True},
    }
    predicate = (active_info or {}).get("predicate")
    if isinstance(predicate, str) and predicate:
        navigation["active_page"]["predicate"] = predicate
    state_paths = (active_info or {}).get("state_paths")
    if isinstance(state_paths, list) and state_paths:
        navigation["active_page"]["state_paths"] = state_paths
    if sidebar_items:
        navigation["sidebar"] = sidebar_items
    return navigation


def _active_slug(active_info: dict | None, page_entries: list[dict]) -> str:
    if isinstance(active_info, dict):
        slug = active_info.get("slug")
        if isinstance(slug, str) and slug:
            return slug
    return str(page_entries[0]["slug"])


def _active_name(active_info: dict | None, active_slug: str, page_entries: list[dict]) -> str:
    if isinstance(active_info, dict):
        name = active_info.get("name")
        if isinstance(name, str) and name:
            return name
    for entry in page_entries:
        if entry["slug"] == active_slug:
            return str(entry["name"])
    return str(page_entries[0]["name"])


def _build_sidebar_items(
    program: ir.Program,
    page_entries: list[dict],
    active_slug: str,
    active_name: str,
) -> list[dict]:
    sidebar = getattr(program, "ui_navigation", None) or _page_level_sidebar(program, active_name)
    if sidebar is None:
        return []
    by_name = {entry["name"]: entry for entry in page_entries}
    items: list[dict] = []
    for entry in getattr(sidebar, "items", []) or []:
        page_entry = by_name.get(entry.page_name)
        if page_entry is None:
            continue
        slug = str(page_entry["slug"])
        items.append(
            {
                "label": entry.label,
                "target_name": page_entry["name"],
                "target_slug": slug,
                "active": slug == active_slug,
            }
        )
    return items


def _page_level_sidebar(program: ir.Program, active_name: str) -> ir.NavigationSidebar | None:
    active_match: ir.NavigationSidebar | None = None
    first_match: ir.NavigationSidebar | None = None
    for page in getattr(program, "pages", []) or []:
        page_sidebar = getattr(page, "ui_navigation", None)
        if page_sidebar is None:
            continue
        if first_match is None:
            first_match = page_sidebar
        if page.name == active_name:
            active_match = page_sidebar
            break
    return active_match or first_match


def _navigation_feature_enabled(program: ir.Program) -> bool:
    if getattr(program, "ui_navigation", None) is not None:
        return True
    if getattr(program, "ui_active_page_rules", None):
        return True
    for page in getattr(program, "pages", []) or []:
        if getattr(page, "ui_navigation", None) is not None:
            return True
        for item in _walk_page_items(getattr(page, "items", []) or []):
            if isinstance(item, ir.ButtonItem):
                if str(getattr(item, "action_kind", "call_flow") or "call_flow") in {"navigate_to", "go_back"}:
                    return True
            if isinstance(item, ir.CardItem):
                for action in getattr(item, "actions", []) or []:
                    if action.kind in {"navigate_to", "go_back"}:
                        return True
            if isinstance(item, ir.TableItem):
                for action in getattr(item, "row_actions", []) or []:
                    if action.kind in {"navigate_to", "go_back"}:
                        return True
            if isinstance(item, ir.ListItem):
                for action in getattr(item, "actions", []) or []:
                    if action.kind in {"navigate_to", "go_back"}:
                        return True
    return False


def _walk_page_items(items: list[ir.PageItem]) -> list[ir.PageItem]:
    seen: list[ir.PageItem] = []
    for item in items:
        seen.append(item)
        if isinstance(item, ir.TabsItem):
            for tab in item.tabs:
                seen.extend(_walk_page_items(tab.children))
            continue
        children = getattr(item, "children", None)
        if isinstance(children, list):
            seen.extend(_walk_page_items(children))
    return seen


__all__ = ["build_navigation"]
