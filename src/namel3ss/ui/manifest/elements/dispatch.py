from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir
from namel3ss.media import MediaValidationMode
from namel3ss.runtime.storage.base import Storage
from namel3ss.schema import records as schema
from namel3ss.ui.manifest.state_defaults import StateContext
from namel3ss.ui.manifest.theme_nodes import apply_theme_overrides
from namel3ss.ui.manifest.visibility import apply_show_when, apply_visibility, evaluate_visibility
from namel3ss.validation import ValidationMode

from .dispatch_actions import dispatch_action_item
from .dispatch_layout import dispatch_layout_item
from .dispatch_misc import dispatch_misc_item
from .dispatch_polish import dispatch_polish_item
from .dispatch_rag import dispatch_rag_item
from .dispatch_views import dispatch_view_item


def _apply_visibility_and_show_when(
    element: dict,
    *,
    visible: bool,
    visibility_info: dict | None,
    show_when_info: dict | None,
) -> dict:
    element = apply_visibility(element, visible, visibility_info)
    return apply_show_when(element, show_when_info)


def page_item_to_manifest(
    item: ir.PageItem,
    record_map: Dict[str, schema.RecordSchema],
    page_name: str,
    page_slug: str,
    path: List[int],
    store: Storage | None,
    identity: dict | None,
    state_ctx: StateContext,
    mode: ValidationMode,
    media_registry: dict[str, Path],
    media_mode: MediaValidationMode,
    warnings: list | None,
    taken_actions: set[str],
    parent_visible: bool,
    build_children,
) -> tuple[dict, Dict[str, dict], bool]:
    predicate_visible, visibility_info = evaluate_visibility(
        getattr(item, "visibility", None),
        getattr(item, "visibility_rule", None),
        state_ctx,
        mode,
        warnings,
        line=getattr(item, "line", None),
        column=getattr(item, "column", None),
    )
    show_when_visible, show_when_info = evaluate_visibility(
        getattr(item, "show_when", None),
        None,
        state_ctx,
        mode,
        warnings,
        line=getattr(item, "line", None),
        column=getattr(item, "column", None),
    )
    effective_visible = parent_visible and predicate_visible and show_when_visible
    handlers = (
        dispatch_misc_item,
        dispatch_view_item,
        dispatch_rag_item,
        dispatch_polish_item,
        dispatch_layout_item,
        dispatch_action_item,
    )
    for handler in handlers:
        result = handler(
            item,
            record_map,
            page_name,
            page_slug,
            path,
            store,
            identity,
            state_ctx,
            mode,
            media_registry,
            media_mode,
            warnings,
            taken_actions,
            build_children,
            effective_visible,
        )
        if result is None:
            continue
        element, actions = result
        element = apply_theme_overrides(element, item, getattr(state_ctx, "ui_theme", None))
        return _apply_visibility_and_show_when(
            element,
            visible=effective_visible,
            visibility_info=visibility_info,
            show_when_info=show_when_info,
        ), actions, effective_visible
    raise Namel3ssError(
        f"Unsupported page item '{type(item)}'",
        line=getattr(item, "line", None),
        column=getattr(item, "column", None),
    )


__all__ = ["page_item_to_manifest"]
