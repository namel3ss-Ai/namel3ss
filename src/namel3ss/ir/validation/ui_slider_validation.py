from __future__ import annotations

from dataclasses import dataclass

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir.model.pages import Page, SliderItem, TabsItem
from namel3ss.ir.model.ui_layout import ConditionalBlock, LayoutDrawer, LayoutGrid, LayoutRow, LayoutStack, LayoutSticky, SidebarLayout


_MISSING_CAPABILITY_MESSAGE = (
    "Capability missing: ui.slider is required to use 'slider' controls. "
    "Add 'capability is ui.slider' to the manifest."
)


@dataclass(frozen=True)
class _SliderUsage:
    line: int | None
    column: int | None


def validate_ui_slider(pages: list[Page], capabilities: tuple[str, ...]) -> None:
    slider_usage: _SliderUsage | None = None
    for page in pages:
        slider_usage = _walk_page_items(page.items, slider_usage)
    if slider_usage is not None and "ui.slider" not in set(capabilities or ()):
        raise Namel3ssError(
            _MISSING_CAPABILITY_MESSAGE,
            line=slider_usage.line,
            column=slider_usage.column,
        )


def _walk_page_items(items: list, slider_usage: _SliderUsage | None) -> _SliderUsage | None:
    _validate_slider_label_uniqueness(items)
    for item in items:
        if isinstance(item, SliderItem):
            _validate_slider_ranges(item)
            if slider_usage is None:
                slider_usage = _SliderUsage(line=item.line, column=item.column)
        if isinstance(item, TabsItem):
            for tab in item.tabs:
                _validate_slider_label_uniqueness(tab.children)
                slider_usage = _walk_page_items(tab.children, slider_usage)
            continue
        if isinstance(item, ConditionalBlock):
            slider_usage = _walk_page_items(item.then_children, slider_usage)
            if item.else_children:
                slider_usage = _walk_page_items(item.else_children, slider_usage)
            continue
        if isinstance(item, SidebarLayout):
            if item.sidebar:
                slider_usage = _walk_page_items(item.sidebar, slider_usage)
            if item.main:
                slider_usage = _walk_page_items(item.main, slider_usage)
            continue
        if isinstance(item, (LayoutStack, LayoutRow, LayoutGrid, LayoutSticky, LayoutDrawer)):
            slider_usage = _walk_page_items(item.children, slider_usage)
            continue
        children = getattr(item, "children", None)
        if isinstance(children, list):
            slider_usage = _walk_page_items(children, slider_usage)
    return slider_usage


def _validate_slider_ranges(item: SliderItem) -> None:
    if item.min_value >= item.max_value:
        raise Namel3ssError(
            f"Slider '{item.label}' requires min < max.",
            line=item.line,
            column=item.column,
        )
    if item.step <= 0:
        raise Namel3ssError(
            f"Slider '{item.label}' requires step > 0.",
            line=item.line,
            column=item.column,
        )


def _validate_slider_label_uniqueness(items: list) -> None:
    labels: dict[str, tuple[int | None, int | None]] = {}
    for item in items:
        if not isinstance(item, SliderItem):
            continue
        label = item.label.strip()
        if not label:
            continue
        previous = labels.get(label)
        if previous is None:
            labels[label] = (item.line, item.column)
            continue
        raise Namel3ssError(
            f"Duplicate control label '{label}' in the same container.",
            line=item.line,
            column=item.column,
        )


__all__ = ["validate_ui_slider"]

