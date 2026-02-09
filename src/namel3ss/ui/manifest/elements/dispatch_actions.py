from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from namel3ss.ir import nodes as ir
from namel3ss.media import MediaValidationMode
from namel3ss.runtime.storage.base import Storage
from namel3ss.schema import records as schema
from namel3ss.ui.manifest.state_defaults import StateContext
from namel3ss.validation import ValidationMode

from . import actions as actions_mod


def dispatch_action_item(
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
    if isinstance(item, ir.ComposeItem):
        return actions_mod.build_compose_item(
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
    if isinstance(item, ir.TitleItem):
        return actions_mod.build_title_item(item, page_name=page_name, page_slug=page_slug, path=path)
    if isinstance(item, ir.TextItem):
        return actions_mod.build_text_item(item, page_name=page_name, page_slug=page_slug, path=path)
    if isinstance(item, ir.TextInputItem):
        return actions_mod.build_text_input_item(
            item,
            page_name=page_name,
            page_slug=page_slug,
            path=path,
            taken_actions=taken_actions,
            state_ctx=state_ctx,
            mode=mode,
            warnings=warnings,
        )
    if isinstance(item, ir.ModalItem):
        return actions_mod.build_modal_item(
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
    if isinstance(item, ir.DrawerItem):
        return actions_mod.build_drawer_item(
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
    if isinstance(item, ir.ButtonItem):
        return actions_mod.build_button_item(
            item,
            page_name=page_name,
            page_slug=page_slug,
            path=path,
            taken_actions=taken_actions,
            state_ctx=state_ctx,
            mode=mode,
            warnings=warnings,
        )
    if isinstance(item, ir.LinkItem):
        return actions_mod.build_link_item(
            item,
            page_name=page_name,
            page_slug=page_slug,
            path=path,
            taken_actions=taken_actions,
        )
    if isinstance(item, ir.SectionItem):
        return actions_mod.build_section_item(
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
    if isinstance(item, ir.CardGroupItem):
        return actions_mod.build_card_group_item(
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
    if isinstance(item, ir.CardItem):
        return actions_mod.build_card_item(
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
    if isinstance(item, ir.RowItem):
        return actions_mod.build_row_item(
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
    if isinstance(item, ir.ColumnItem):
        return actions_mod.build_column_item(
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
    if isinstance(item, ir.DividerItem):
        return actions_mod.build_divider_item(item, page_name=page_name, page_slug=page_slug, path=path)
    if isinstance(item, ir.ImageItem):
        return actions_mod.build_image_item(
            item,
            page_name=page_name,
            page_slug=page_slug,
            path=path,
            media_registry=media_registry,
            media_mode=media_mode,
            warnings=warnings,
        )
    return None


__all__ = ["dispatch_action_item"]
