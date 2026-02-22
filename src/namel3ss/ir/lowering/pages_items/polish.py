from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.icons.registry import validate_icon_name
from namel3ss.ir.lowering.expressions import _lower_expression
from namel3ss.ir.model.expressions import StatePath as IRStatePath
from namel3ss.ir.model.pages import BadgeItem, GridItem, IconItem, LightboxItem, LoadingItem, PageItem, SnackbarItem


def lower_grid_item(
    item: ast.GridItem,
    record_map,
    flow_names: set[str],
    page_name: str,
    page_names: set[str],
    overlays: dict[str, set[str]],
    compose_names: set[str],
    *,
    lower_page_item,
    attach_origin,
) -> GridItem:
    children: list[PageItem] = [
        lower_page_item(child, record_map, flow_names, page_name, page_names, overlays, compose_names)
        for child in item.children
    ]
    return attach_origin(
        GridItem(
            columns=list(getattr(item, "columns", []) or []),
            children=children,
            line=item.line,
            column=item.column,
        ),
        item,
    )


def lower_loading_item(item: ast.LoadingItem, *, attach_origin) -> LoadingItem:
    return attach_origin(
        LoadingItem(
            variant=str(getattr(item, "variant", "spinner") or "spinner"),
            line=item.line,
            column=item.column,
        ),
        item,
    )


def lower_badge_item(item: ast.BadgeItem, *, attach_origin) -> BadgeItem:
    source = getattr(item, "source", None)
    lowered = _lower_expression(source) if isinstance(source, ast.Expression) else source
    if not isinstance(lowered, IRStatePath):
        raise Namel3ssError(
            "Badges must bind to state.<path>.",
            line=item.line,
            column=item.column,
        )
    return attach_origin(
        BadgeItem(
            source=lowered,
            style=str(getattr(item, "style", "neutral") or "neutral"),
            line=item.line,
            column=item.column,
        ),
        item,
    )

def lower_snackbar_item(item: ast.SnackbarItem, *, attach_origin) -> SnackbarItem:
    return attach_origin(
        SnackbarItem(
            message=str(getattr(item, "message", "") or ""),
            duration=int(getattr(item, "duration", 3000) or 3000),
            line=item.line,
            column=item.column,
        ),
        item,
    )


def lower_icon_item(item: ast.IconItem, *, attach_origin) -> IconItem:
    icon_name = validate_icon_name(
        str(getattr(item, "name", "") or ""),
        line=item.line,
        column=item.column,
    )
    return attach_origin(
        IconItem(
            name=icon_name,
            size=str(getattr(item, "size", "medium") or "medium"),
            role=str(getattr(item, "role", "decorative") or "decorative"),
            label=getattr(item, "label", None),
            line=item.line,
            column=item.column,
        ),
        item,
    )


def lower_lightbox_item(item: ast.LightboxItem, *, attach_origin) -> LightboxItem:
    images = [str(value) for value in list(getattr(item, "images", []) or []) if str(value)]
    return attach_origin(
        LightboxItem(
            images=images,
            start_index=int(getattr(item, "start_index", 0) or 0),
            line=item.line,
            column=item.column,
        ),
        item,
    )


__all__ = [
    "lower_badge_item",
    "lower_grid_item",
    "lower_icon_item",
    "lower_lightbox_item",
    "lower_loading_item",
    "lower_snackbar_item",
]
