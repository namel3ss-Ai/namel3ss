from __future__ import annotations

from namel3ss.ui.settings import UI_DEFAULTS

SPACING_TOKENS: tuple[str, ...] = ("xs", "s", "m", "l", "xl", "xxl")

_DENSITY_ROLE_MAP: dict[str, dict[str, str]] = {
    "compact": {"tight": "xs", "base": "s", "loose": "m", "roomy": "l"},
    "comfortable": {"tight": "s", "base": "m", "loose": "l", "roomy": "xl"},
    "spacious": {"tight": "m", "base": "l", "loose": "xl", "roomy": "xxl"},
}

_CONTAINER_SPACING_RULES: dict[str, tuple[tuple[str, str], ...]] = {
    "compose": (("padding", "base"), ("gap", "base")),
    "section": (("padding", "base"), ("gap", "loose"), ("title_gap", "tight")),
    "card": (
        ("padding", "base"),
        ("gap", "base"),
        ("title_gap", "tight"),
        ("stat_gap", "tight"),
        ("actions_gap", "tight"),
    ),
    "card_group": (("gap", "loose"),),
    "row": (("gap", "base"),),
    "column": (("gap", "base"),),
    "tabs": (("tab_gap", "tight"), ("header_gap", "base")),
    "tab": (("gap", "base"),),
    "modal": (("padding", "loose"), ("header_gap", "tight"), ("body_gap", "base")),
    "drawer": (("padding", "loose"), ("header_gap", "tight"), ("body_gap", "base")),
}

_COMPONENT_SPACING_RULES: dict[str, tuple[tuple[str, str], ...]] = {
    "form": (("field_gap", "base"), ("group_gap", "loose"), ("section_gap", "roomy"), ("help_gap", "tight")),
    "table": (("header_gap", "base"), ("row_gap", "tight"), ("cell_gap", "tight"), ("row_actions_gap", "tight")),
    "list": (("item_gap", "base"), ("secondary_gap", "tight"), ("meta_gap", "tight")),
    "chart": (("series_gap", "base"), ("summary_gap", "base"), ("legend_gap", "tight")),
    "chat": (("section_gap", "base"), ("message_gap", "base"), ("composer_gap", "base")),
    "messages": (("item_gap", "base"), ("meta_gap", "tight")),
    "composer": (("input_gap", "tight"), ("action_gap", "tight")),
    "thinking": (("status_gap", "tight"),),
    "citations": (("item_gap", "tight"),),
    "memory": (("item_gap", "tight"),),
}

_VIEW_SPACING_RULES: dict[str, tuple[tuple[str, str], ...]] = {
    "table": _COMPONENT_SPACING_RULES["table"],
    "list": _COMPONENT_SPACING_RULES["list"],
}


def spacing_tokens_for_density(density: str | None) -> dict[str, str]:
    if not density:
        density = UI_DEFAULTS["density"]
    return _DENSITY_ROLE_MAP.get(density, _DENSITY_ROLE_MAP[UI_DEFAULTS["density"]])


def spacing_for_element(element: dict, density: str | None) -> dict[str, str] | None:
    if not isinstance(element, dict):
        return None
    element_type = element.get("type")
    if not isinstance(element_type, str):
        return None
    roles = None
    if element_type == "view":
        representation = element.get("representation")
        if isinstance(representation, str):
            roles = _VIEW_SPACING_RULES.get(representation)
    if roles is None:
        roles = _CONTAINER_SPACING_RULES.get(element_type) or _COMPONENT_SPACING_RULES.get(element_type)
    if not roles:
        return None
    role_map = spacing_tokens_for_density(density)
    return {key: role_map[role] for key, role in roles}


def apply_spacing_to_elements(elements: list[dict], density: str | None) -> None:
    for element in elements or []:
        if not isinstance(element, dict):
            continue
        spacing = spacing_for_element(element, density)
        if spacing:
            element["spacing"] = spacing
        children = element.get("children")
        if isinstance(children, list):
            apply_spacing_to_elements(children, density)


def apply_spacing_to_pages(pages: list[dict], density: str | None) -> None:
    for page in pages or []:
        if not isinstance(page, dict):
            continue
        elements = page.get("elements")
        if isinstance(elements, list):
            apply_spacing_to_elements(elements, density)


__all__ = [
    "SPACING_TOKENS",
    "apply_spacing_to_elements",
    "apply_spacing_to_pages",
    "spacing_for_element",
    "spacing_tokens_for_density",
]
