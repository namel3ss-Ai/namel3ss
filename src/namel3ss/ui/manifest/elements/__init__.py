from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir
from namel3ss.media import MediaValidationMode
from namel3ss.runtime.storage.base import Storage
from namel3ss.schema import records as schema
from namel3ss.ui.manifest.state_defaults import StateContext
from namel3ss.validation import ValidationMode

from . import actions as actions_mod
from . import numbers as numbers_mod
from . import story as story_mod
from . import views as views_mod


def _build_children(
    children: List[ir.PageItem],
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
) -> tuple[List[dict], Dict[str, dict]]:
    elements: List[dict] = []
    actions: Dict[str, dict] = {}
    for idx, child in enumerate(children):
        element, child_actions = _page_item_to_manifest(
            child,
            record_map,
            page_name,
            page_slug,
            path + [idx],
            store,
            identity,
            state_ctx,
            mode,
            media_registry,
            media_mode,
            warnings,
            taken_actions,
        )
        elements.append(element)
        for action_id, action_entry in child_actions.items():
            if action_id in actions:
                raise Namel3ssError(
                    f"Duplicate action id '{action_id}'. Use a unique id or omit to auto-generate.",
                    line=child.line,
                    column=child.column,
                )
            actions[action_id] = action_entry
            taken_actions.add(action_id)
    return elements, actions


def _page_item_to_manifest(
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
) -> tuple[dict, Dict[str, dict]]:
    if isinstance(item, ir.NumberItem):
        return numbers_mod.build_number_item(item, page_name=page_name, page_slug=page_slug, path=path)
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
            build_children=_build_children,
        )
    if isinstance(item, ir.StoryItem):
        return story_mod.build_story_item(
            item,
            page_name=page_name,
            page_slug=page_slug,
            path=path,
            state_ctx=state_ctx,
            media_registry=media_registry,
            media_mode=media_mode,
            warnings=warnings,
        )
    if isinstance(item, ir.TitleItem):
        return actions_mod.build_title_item(item, page_name=page_name, page_slug=page_slug, path=path)
    if isinstance(item, ir.TextItem):
        return actions_mod.build_text_item(item, page_name=page_name, page_slug=page_slug, path=path)
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
            build_children=_build_children,
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
            build_children=_build_children,
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
            build_children=_build_children,
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
            build_children=_build_children,
        )
    if isinstance(item, ir.ButtonItem):
        return actions_mod.build_button_item(
            item,
            page_name=page_name,
            page_slug=page_slug,
            path=path,
            taken_actions=taken_actions,
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
            build_children=_build_children,
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
            build_children=_build_children,
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
            build_children=_build_children,
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
            build_children=_build_children,
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
            build_children=_build_children,
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
    raise Namel3ssError(
        f"Unsupported page item '{type(item)}'",
        line=getattr(item, "line", None),
        column=getattr(item, "column", None),
    )


__all__ = ["_build_children"]
