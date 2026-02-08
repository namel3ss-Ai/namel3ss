from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir
from namel3ss.media import MediaValidationMode
from namel3ss.runtime.storage.base import Storage
from namel3ss.schema import records as schema
from namel3ss.ui import manifest_rag as rag_mod
from namel3ss.ui.manifest.state_defaults import StateContext
from namel3ss.ui.manifest.visibility import apply_visibility, evaluate_visibility
from namel3ss.validation import ValidationMode

from . import actions as actions_mod
from . import numbers as numbers_mod
from . import polish as polish_mod
from . import story as story_mod
from . import views as views_mod
from .custom_component import build_custom_component_element


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
    effective_visible = parent_visible and predicate_visible
    if isinstance(item, ir.NumberItem):
        element, actions = numbers_mod.build_number_item(item, page_name=page_name, page_slug=page_slug, path=path)
        return apply_visibility(element, effective_visible, visibility_info), actions, effective_visible
    if isinstance(item, ir.ViewItem):
        element, actions = views_mod.build_view_item(
            item,
            record_map,
            page_name=page_name,
            page_slug=page_slug,
            path=path,
            store=store,
            identity=identity,
        )
        return apply_visibility(element, effective_visible, visibility_info), actions, effective_visible
    if isinstance(item, ir.ComposeItem):
        element, actions = actions_mod.build_compose_item(
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
            parent_visible=effective_visible,
        )
        return apply_visibility(element, effective_visible, visibility_info), actions, effective_visible
    if isinstance(item, ir.StoryItem):
        element, actions = story_mod.build_story_item(
            item,
            page_name=page_name,
            page_slug=page_slug,
            path=path,
            state_ctx=state_ctx,
            media_registry=media_registry,
            media_mode=media_mode,
            warnings=warnings,
        )
        return apply_visibility(element, effective_visible, visibility_info), actions, effective_visible
    if isinstance(item, ir.TitleItem):
        element, actions = actions_mod.build_title_item(item, page_name=page_name, page_slug=page_slug, path=path)
        return apply_visibility(element, effective_visible, visibility_info), actions, effective_visible
    if isinstance(item, ir.TextItem):
        element, actions = actions_mod.build_text_item(item, page_name=page_name, page_slug=page_slug, path=path)
        return apply_visibility(element, effective_visible, visibility_info), actions, effective_visible
    if isinstance(item, ir.TextInputItem):
        element, actions = actions_mod.build_text_input_item(
            item,
            page_name=page_name,
            page_slug=page_slug,
            path=path,
            taken_actions=taken_actions,
            state_ctx=state_ctx,
            mode=mode,
            warnings=warnings,
        )
        return apply_visibility(element, effective_visible, visibility_info), actions, effective_visible
    if isinstance(item, ir.UploadItem):
        element, actions = views_mod.build_upload_item(
            item,
            page_name=page_name,
            page_slug=page_slug,
            path=path,
            taken_actions=taken_actions,
            state_ctx=state_ctx,
        )
        return apply_visibility(element, effective_visible, visibility_info), actions, effective_visible
    if isinstance(item, ir.LoadingItem):
        element, actions = polish_mod.build_loading_item(
            item,
            page_name=page_name,
            page_slug=page_slug,
            path=path,
        )
        return apply_visibility(element, effective_visible, visibility_info), actions, effective_visible
    if isinstance(item, ir.SnackbarItem):
        element, actions = polish_mod.build_snackbar_item(
            item,
            page_name=page_name,
            page_slug=page_slug,
            path=path,
        )
        return apply_visibility(element, effective_visible, visibility_info), actions, effective_visible
    if isinstance(item, ir.IconItem):
        element, actions = polish_mod.build_icon_item(
            item,
            page_name=page_name,
            page_slug=page_slug,
            path=path,
        )
        return apply_visibility(element, effective_visible, visibility_info), actions, effective_visible
    if isinstance(item, ir.LightboxItem):
        element, actions = polish_mod.build_lightbox_item(
            item,
            page_name=page_name,
            page_slug=page_slug,
            path=path,
        )
        return apply_visibility(element, effective_visible, visibility_info), actions, effective_visible
    if isinstance(item, ir.FormItem):
        element, actions = views_mod.build_form_item(
            item,
            record_map,
            page_name=page_name,
            page_slug=page_slug,
            path=path,
            taken_actions=taken_actions,
        )
        return apply_visibility(element, effective_visible, visibility_info), actions, effective_visible
    if isinstance(item, ir.TableItem):
        element, actions = views_mod.build_table_item(
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
        return apply_visibility(element, effective_visible, visibility_info), actions, effective_visible
    if isinstance(item, ir.ListItem):
        element, actions = views_mod.build_list_item(
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
        return apply_visibility(element, effective_visible, visibility_info), actions, effective_visible
    if isinstance(item, ir.ChartItem):
        element, actions = views_mod.build_chart_item(
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
        return apply_visibility(element, effective_visible, visibility_info), actions, effective_visible
    if isinstance(item, ir.CustomComponentItem):
        element, actions = build_custom_component_element(
            item,
            page_name=page_name,
            page_slug=page_slug,
            path=path,
            state_ctx=state_ctx,
        )
        return apply_visibility(element, effective_visible, visibility_info), actions, effective_visible
    if isinstance(item, ir.ChatItem):
        element, actions = views_mod.build_chat_item(
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
            parent_visible=effective_visible,
        )
        return apply_visibility(element, effective_visible, visibility_info), actions, effective_visible
    if isinstance(item, ir.CitationChipsItem):
        element, actions = rag_mod.build_citation_chips_item(
            item,
            page_name=page_name,
            page_slug=page_slug,
            path=path,
            state_ctx=state_ctx,
            mode=mode,
            warnings=warnings,
        )
        return apply_visibility(element, effective_visible, visibility_info), actions, effective_visible
    if isinstance(item, ir.SourcePreviewItem):
        element, actions = rag_mod.build_source_preview_item(
            item,
            page_name=page_name,
            page_slug=page_slug,
            path=path,
            state_ctx=state_ctx,
        )
        return apply_visibility(element, effective_visible, visibility_info), actions, effective_visible
    if isinstance(item, ir.TrustIndicatorItem):
        element, actions = rag_mod.build_trust_indicator_item(
            item,
            page_name=page_name,
            page_slug=page_slug,
            path=path,
            state_ctx=state_ctx,
        )
        return apply_visibility(element, effective_visible, visibility_info), actions, effective_visible
    if isinstance(item, ir.ScopeSelectorItem):
        element, actions = rag_mod.build_scope_selector_item(
            item,
            page_name=page_name,
            page_slug=page_slug,
            path=path,
            state_ctx=state_ctx,
        )
        return apply_visibility(element, effective_visible, visibility_info), actions, effective_visible
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
        element, actions = chat_result
        return apply_visibility(element, effective_visible, visibility_info), actions, effective_visible
    if isinstance(item, ir.ModalItem):
        element, actions = actions_mod.build_modal_item(
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
            parent_visible=effective_visible,
        )
        return apply_visibility(element, effective_visible, visibility_info), actions, effective_visible
    if isinstance(item, ir.DrawerItem):
        element, actions = actions_mod.build_drawer_item(
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
            parent_visible=effective_visible,
        )
        return apply_visibility(element, effective_visible, visibility_info), actions, effective_visible
    if isinstance(item, ir.TabsItem):
        element, actions = views_mod.build_tabs_item(
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
            parent_visible=effective_visible,
        )
        return apply_visibility(element, effective_visible, visibility_info), actions, effective_visible
    if isinstance(item, ir.ButtonItem):
        element, actions = actions_mod.build_button_item(
            item,
            page_name=page_name,
            page_slug=page_slug,
            path=path,
            taken_actions=taken_actions,
            state_ctx=state_ctx,
            mode=mode,
            warnings=warnings,
        )
        return apply_visibility(element, effective_visible, visibility_info), actions, effective_visible
    if isinstance(item, ir.LinkItem):
        element, actions = actions_mod.build_link_item(
            item,
            page_name=page_name,
            page_slug=page_slug,
            path=path,
            taken_actions=taken_actions,
        )
        return apply_visibility(element, effective_visible, visibility_info), actions, effective_visible
    if isinstance(item, ir.SectionItem):
        element, actions = actions_mod.build_section_item(
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
            parent_visible=effective_visible,
        )
        return apply_visibility(element, effective_visible, visibility_info), actions, effective_visible
    if isinstance(item, ir.CardGroupItem):
        element, actions = actions_mod.build_card_group_item(
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
            parent_visible=effective_visible,
        )
        return apply_visibility(element, effective_visible, visibility_info), actions, effective_visible
    if isinstance(item, ir.CardItem):
        element, actions = actions_mod.build_card_item(
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
            parent_visible=effective_visible,
        )
        return apply_visibility(element, effective_visible, visibility_info), actions, effective_visible
    if isinstance(item, ir.RowItem):
        element, actions = actions_mod.build_row_item(
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
            parent_visible=effective_visible,
        )
        return apply_visibility(element, effective_visible, visibility_info), actions, effective_visible
    if isinstance(item, ir.ColumnItem):
        element, actions = actions_mod.build_column_item(
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
            parent_visible=effective_visible,
        )
        return apply_visibility(element, effective_visible, visibility_info), actions, effective_visible
    if isinstance(item, ir.GridItem):
        element, actions = polish_mod.build_grid_item(
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
            parent_visible=effective_visible,
        )
        return apply_visibility(element, effective_visible, visibility_info), actions, effective_visible
    if isinstance(item, ir.DividerItem):
        element, actions = actions_mod.build_divider_item(item, page_name=page_name, page_slug=page_slug, path=path)
        return apply_visibility(element, effective_visible, visibility_info), actions, effective_visible
    if isinstance(item, ir.ImageItem):
        element, actions = actions_mod.build_image_item(
            item,
            page_name=page_name,
            page_slug=page_slug,
            path=path,
            media_registry=media_registry,
            media_mode=media_mode,
            warnings=warnings,
        )
        return apply_visibility(element, effective_visible, visibility_info), actions, effective_visible
    raise Namel3ssError(
        f"Unsupported page item '{type(item)}'",
        line=getattr(item, "line", None),
        column=getattr(item, "column", None),
    )


__all__ = ["page_item_to_manifest"]
