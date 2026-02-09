from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from namel3ss.ir import nodes as ir
from namel3ss.media import MediaValidationMode
from namel3ss.runtime.storage.base import Storage
from namel3ss.schema import records as schema
from namel3ss.ui.manifest import layout_nodes as layout_mod
from namel3ss.ui.manifest.state_defaults import StateContext
from namel3ss.validation import ValidationMode


def dispatch_layout_item(
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
    build_children,
    parent_visible: bool,
) -> tuple[dict, Dict[str, dict]] | None:
    if isinstance(item, ir.LayoutStack):
        return layout_mod.build_layout_stack(
            item,
            record_map,
            page_name=page_name,
            page_slug=page_slug,
            path=path,
            store=store,
            identity=identity,
            state_ctx=state_ctx,
            mode=mode,
            media_registry=media_registry,
            media_mode=media_mode,
            warnings=warnings,
            taken_actions=taken_actions,
            build_children=build_children,
            parent_visible=parent_visible,
        )
    if isinstance(item, ir.LayoutRow):
        return layout_mod.build_layout_row(
            item,
            record_map,
            page_name=page_name,
            page_slug=page_slug,
            path=path,
            store=store,
            identity=identity,
            state_ctx=state_ctx,
            mode=mode,
            media_registry=media_registry,
            media_mode=media_mode,
            warnings=warnings,
            taken_actions=taken_actions,
            build_children=build_children,
            parent_visible=parent_visible,
        )
    if isinstance(item, ir.LayoutColumn):
        return layout_mod.build_layout_column(
            item,
            record_map,
            page_name=page_name,
            page_slug=page_slug,
            path=path,
            store=store,
            identity=identity,
            state_ctx=state_ctx,
            mode=mode,
            media_registry=media_registry,
            media_mode=media_mode,
            warnings=warnings,
            taken_actions=taken_actions,
            build_children=build_children,
            parent_visible=parent_visible,
        )
    if isinstance(item, ir.LayoutGrid):
        return layout_mod.build_layout_grid(
            item,
            record_map,
            page_name=page_name,
            page_slug=page_slug,
            path=path,
            store=store,
            identity=identity,
            state_ctx=state_ctx,
            mode=mode,
            media_registry=media_registry,
            media_mode=media_mode,
            warnings=warnings,
            taken_actions=taken_actions,
            build_children=build_children,
            parent_visible=parent_visible,
        )
    if isinstance(item, ir.SidebarLayout):
        return layout_mod.build_sidebar_layout(
            item,
            record_map,
            page_name=page_name,
            page_slug=page_slug,
            path=path,
            store=store,
            identity=identity,
            state_ctx=state_ctx,
            mode=mode,
            media_registry=media_registry,
            media_mode=media_mode,
            warnings=warnings,
            taken_actions=taken_actions,
            build_children=build_children,
            parent_visible=parent_visible,
        )
    if isinstance(item, ir.LayoutDrawer):
        return layout_mod.build_layout_drawer(
            item,
            record_map,
            page_name=page_name,
            page_slug=page_slug,
            path=path,
            store=store,
            identity=identity,
            state_ctx=state_ctx,
            mode=mode,
            media_registry=media_registry,
            media_mode=media_mode,
            warnings=warnings,
            taken_actions=taken_actions,
            build_children=build_children,
            parent_visible=parent_visible,
        )
    if isinstance(item, ir.LayoutSticky):
        return layout_mod.build_layout_sticky(
            item,
            record_map,
            page_name=page_name,
            page_slug=page_slug,
            path=path,
            store=store,
            identity=identity,
            state_ctx=state_ctx,
            mode=mode,
            media_registry=media_registry,
            media_mode=media_mode,
            warnings=warnings,
            taken_actions=taken_actions,
            build_children=build_children,
            parent_visible=parent_visible,
        )
    if isinstance(item, ir.ConditionalBlock):
        return layout_mod.build_conditional_block(
            item,
            record_map,
            page_name=page_name,
            page_slug=page_slug,
            path=path,
            store=store,
            identity=identity,
            state_ctx=state_ctx,
            mode=mode,
            media_registry=media_registry,
            media_mode=media_mode,
            warnings=warnings,
            taken_actions=taken_actions,
            build_children=build_children,
            parent_visible=parent_visible,
        )
    return None


__all__ = ["dispatch_layout_item"]
