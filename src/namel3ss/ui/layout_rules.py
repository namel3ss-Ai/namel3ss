from __future__ import annotations

from dataclasses import dataclass

FLAT_PAGE_ELEMENT_THRESHOLD = 8
FLAT_PAGE_LEAF_THRESHOLD = 6
UNGROUPED_DATA_HEAVY_THRESHOLD = 3
ACTION_HEAVY_THRESHOLD = 4
MAX_NESTING_DEPTH = 4
MAX_ROW_COLUMNS = 3

CONTAINER_TYPES = {
    "card",
    "card_group",
    "column",
    "compose",
    "drawer",
    "modal",
    "row",
    "section",
    "tab",
    "tabs",
}
OVERLAY_TYPES = {"modal", "drawer"}
ACTION_ELEMENT_TYPES = {"button", "link"}
DATA_HEAVY_TYPES = {"table", "list", "form", "chart", "view"}

LABEL_FIELDS = {
    "card": "label",
    "compose": "name",
    "drawer": "label",
    "modal": "label",
    "section": "label",
    "tab": "label",
}


@dataclass(frozen=True)
class LayoutLocation:
    page: str
    page_slug: str
    path: str | None
    line: int | None
    column: int | None

    def sort_key(self) -> tuple[str, str, int, int]:
        return (
            self.page_slug or "",
            self.path or "",
            self.line or 0,
            self.column or 0,
        )


@dataclass(frozen=True)
class LayoutFinding:
    code: str
    message: str
    fix: str
    location: LayoutLocation

    def sort_key(self) -> tuple[str, str, str, int, int, str]:
        page_slug, path, line, column = self.location.sort_key()
        return (page_slug, path, self.code, line, column, self.message)


def is_container_type(element_type: str | None) -> bool:
    return element_type in CONTAINER_TYPES


def is_overlay_type(element_type: str | None) -> bool:
    return element_type in OVERLAY_TYPES


def is_action_element(element_type: str | None) -> bool:
    return element_type in ACTION_ELEMENT_TYPES


def is_data_heavy_element(element: dict) -> bool:
    element_type = element.get("type")
    if element_type == "view":
        return element.get("representation") in {"table", "list"}
    return element_type in DATA_HEAVY_TYPES


def record_representation(element: dict) -> str | None:
    element_type = element.get("type")
    if element_type == "table":
        return "table"
    if element_type == "list":
        return "list"
    if element_type == "view":
        representation = element.get("representation")
        if representation in {"table", "list"}:
            return representation
    return None


def container_label(element: dict) -> str | None:
    element_type = element.get("type")
    label_key = LABEL_FIELDS.get(element_type)
    if not label_key:
        return None
    value = element.get(label_key)
    if value is None:
        return None
    if isinstance(value, str):
        trimmed = value.strip()
        return trimmed if trimmed else None
    return str(value)


def is_labeled_container(element: dict) -> bool:
    return container_label(element) is not None


def rule_flat_page_sprawl(
    *,
    page_name: str,
    page_slug: str,
    element_count: int,
    leaf_count: int,
    location: LayoutLocation,
) -> LayoutFinding | None:
    if element_count < FLAT_PAGE_ELEMENT_THRESHOLD or leaf_count < FLAT_PAGE_LEAF_THRESHOLD:
        return None
    return LayoutFinding(
        code="layout.flat_page_sprawl",
        message=(
            f'Page "{page_name}" has {leaf_count} top-level items across {element_count} elements '
            "without grouping."
        ),
        fix="Group related items into sections, cards, or tabs.",
        location=location,
    )


def rule_ungrouped_data_heavy(
    *,
    page_name: str,
    page_slug: str,
    count: int,
    location: LayoutLocation,
) -> LayoutFinding | None:
    if count < UNGROUPED_DATA_HEAVY_THRESHOLD:
        return None
    return LayoutFinding(
        code="layout.data_ungrouped",
        message=f'Page "{page_name}" has {count} data-heavy elements without grouping.',
        fix="Place tables, lists, forms, or charts inside labeled sections or cards.",
        location=location,
    )


def rule_action_heavy_container(
    *,
    container_type: str,
    label: str | None,
    action_count: int,
    location: LayoutLocation,
) -> LayoutFinding | None:
    if action_count < ACTION_HEAVY_THRESHOLD:
        return None
    label_text = f' "{label}"' if label else ""
    return LayoutFinding(
        code="layout.action_heavy",
        message=(
            f'Container {container_type}{label_text} on page "{location.page}" has {action_count} actions.'
        ),
        fix="Split actions into smaller groups or move them into focused cards.",
        location=location,
    )


def rule_mixed_record_representation(
    *,
    record_name: str,
    representations: list[str],
    location: LayoutLocation,
) -> LayoutFinding:
    joined = ", ".join(representations)
    return LayoutFinding(
        code="layout.mixed_record_representation",
        message=f'Record "{record_name}" appears with mixed representations: {joined}.',
        fix="Use a single representation (table or list) for the same record across pages.",
        location=location,
    )


def rule_inconsistent_columns(
    *,
    record_name: str,
    config_count: int,
    location: LayoutLocation,
) -> LayoutFinding:
    return LayoutFinding(
        code="layout.inconsistent_columns",
        message=f'Record "{record_name}" tables use {config_count} different column configurations.',
        fix="Align column selections for consistent record presentation.",
        location=location,
    )


def rule_deep_nesting(
    *,
    container_type: str,
    depth: int,
    location: LayoutLocation,
) -> LayoutFinding | None:
    if depth <= MAX_NESTING_DEPTH:
        return None
    return LayoutFinding(
        code="layout.deep_nesting",
        message=(
            f'Container {container_type} on page "{location.page}" nests {depth} levels deep.'
        ),
        fix="Flatten container nesting to improve layout clarity.",
        location=location,
    )


def rule_grid_sprawl(
    *,
    column_count: int,
    location: LayoutLocation,
) -> LayoutFinding | None:
    if column_count <= MAX_ROW_COLUMNS:
        return None
    return LayoutFinding(
        code="layout.grid_sprawl",
        message=(
            f'Row on page "{location.page}" has {column_count} columns, which is hard to scan.'
        ),
        fix="Reduce columns per row or split into multiple rows.",
        location=location,
    )


def rule_unlabeled_container(
    *,
    container_type: str,
    location: LayoutLocation,
) -> LayoutFinding:
    return LayoutFinding(
        code="layout.unlabeled_container",
        message=f'Container {container_type} on page "{location.page}" has no label.',
        fix="Provide a label to clarify the purpose of this container.",
        location=location,
    )


__all__ = [
    "ACTION_ELEMENT_TYPES",
    "ACTION_HEAVY_THRESHOLD",
    "CONTAINER_TYPES",
    "DATA_HEAVY_TYPES",
    "FLAT_PAGE_ELEMENT_THRESHOLD",
    "FLAT_PAGE_LEAF_THRESHOLD",
    "LABEL_FIELDS",
    "LayoutFinding",
    "LayoutLocation",
    "MAX_NESTING_DEPTH",
    "MAX_ROW_COLUMNS",
    "OVERLAY_TYPES",
    "UNGROUPED_DATA_HEAVY_THRESHOLD",
    "container_label",
    "is_action_element",
    "is_container_type",
    "is_data_heavy_element",
    "is_labeled_container",
    "is_overlay_type",
    "record_representation",
    "rule_action_heavy_container",
    "rule_deep_nesting",
    "rule_flat_page_sprawl",
    "rule_grid_sprawl",
    "rule_inconsistent_columns",
    "rule_mixed_record_representation",
    "rule_ungrouped_data_heavy",
    "rule_unlabeled_container",
]
