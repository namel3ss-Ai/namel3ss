from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from namel3ss.ir import nodes as ir
from namel3ss.media import MediaValidationMode
from namel3ss.runtime.storage.base import Storage
from namel3ss.schema import records as schema
from namel3ss.ui.manifest.state_defaults import StateContext
from namel3ss.validation import ValidationMode

from . import views as views_mod
from namel3ss.ui.manifest.components.slider_component import build_slider_component
from namel3ss.ui.manifest.components.tooltip_component import build_tooltip_component


def dispatch_view_item(
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
    if isinstance(item, ir.ViewItem):
        return views_mod.build_view_item(
            item,
            record_map,
            page_name=page_name,
            page_slug=page_slug,
            path=path,
            store=store,
            identity=identity,
        )
    if isinstance(item, ir.UploadItem):
        return views_mod.build_upload_item(
            item,
            page_name=page_name,
            page_slug=page_slug,
            path=path,
            taken_actions=taken_actions,
            state_ctx=state_ctx,
        )
    if isinstance(item, ir.FormItem):
        return views_mod.build_form_item(
            item,
            record_map,
            page_name=page_name,
            page_slug=page_slug,
            path=path,
            taken_actions=taken_actions,
        )
    if isinstance(item, ir.TableItem):
        return views_mod.build_table_item(
            item,
            record_map,
            page_name,
            page_slug,
            path=path,
            store=store,
            identity=identity,
            state_ctx=state_ctx,
            mode=mode,
            warnings=warnings,
        )
    if isinstance(item, ir.ListItem):
        return views_mod.build_list_item(
            item,
            record_map,
            page_name=page_name,
            page_slug=page_slug,
            path=path,
            store=store,
            identity=identity,
            state_ctx=state_ctx,
            mode=mode,
            warnings=warnings,
        )
    if isinstance(item, ir.ChartItem):
        return views_mod.build_chart_item(
            item,
            record_map,
            page_name=page_name,
            page_slug=page_slug,
            path=path,
            store=store,
            identity=identity,
            state_ctx=state_ctx,
            mode=mode,
            warnings=warnings,
        )
    if isinstance(item, ir.SliderItem):
        return build_slider_component(
            item,
            page_name=page_name,
            page_slug=page_slug,
            path=path,
            state_ctx=state_ctx,
            taken_actions=taken_actions,
        )
    if isinstance(item, ir.TooltipItem):
        return build_tooltip_component(
            item,
            page_name=page_name,
            page_slug=page_slug,
            path=path,
        )
    if isinstance(item, ir.ChatItem):
        return views_mod.build_chat_item(
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
    if isinstance(item, ir.TabsItem):
        return views_mod.build_tabs_item(
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
    chat_result = views_mod.build_chat_child_item(
        item,
        page_name=page_name,
        page_slug=page_slug,
        path=path,
        state_ctx=state_ctx,
        mode=mode,
        warnings=warnings,
    )
    if chat_result is not None:
        return chat_result
    return None


__all__ = ["dispatch_view_item"]
