from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir
from namel3ss.media import MediaValidationMode
from namel3ss.runtime.storage.base import Storage
from namel3ss.schema import records as schema
from namel3ss.ui.manifest.canonical import _element_id
from namel3ss.ui.manifest.elements.base import _base_element
from namel3ss.ui.manifest.state_defaults import StateContext
from namel3ss.ui.manifest.visibility import apply_visibility, evaluate_visibility
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
    parent_visible: bool = True,
) -> tuple[List[dict], Dict[str, dict]]:
    elements: List[dict] = []
    actions: Dict[str, dict] = {}
    for idx, child in enumerate(children):
        seen_before = set(taken_actions)
        element, child_actions, child_visible = _page_item_to_manifest(
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
            parent_visible,
        )
        elements.append(element)
        source_element_id = element.get("element_id") if isinstance(element, dict) else None
        is_debug_only = bool(element.get("debug_only")) if isinstance(element, dict) else False
        if isinstance(source_element_id, str):
            for action_entry in child_actions.values():
                if isinstance(action_entry, dict):
                    action_entry.setdefault("_source_element_id", source_element_id)
                    if is_debug_only:
                        action_entry.setdefault("debug_only", True)
        for action_id, action_entry in child_actions.items():
            if action_id in seen_before:
                raise Namel3ssError(
                    f"Duplicate action id '{action_id}'. Use a unique id or omit to auto-generate.",
                    line=child.line,
                    column=child.column,
                )
            taken_actions.add(action_id)
            if child_visible:
                actions[action_id] = action_entry
    return elements, actions


def _build_custom_component_element(
    item: ir.CustomComponentItem,
    *,
    page_name: str,
    page_slug: str,
    path: List[int],
    state_ctx: StateContext,
) -> tuple[dict, Dict[str, dict]]:
    registry = getattr(state_ctx, "ui_plugin_registry", None)
    if registry is None:
        raise Namel3ssError(
            "Custom UI component registry is not initialized.",
            line=getattr(item, "line", None),
            column=getattr(item, "column", None),
        )
    props: dict[str, object] = {}
    for prop in list(getattr(item, "properties", []) or []):
        key = str(getattr(prop, "name", "") or "")
        if not key:
            continue
        props[key] = _resolve_component_prop_value(getattr(prop, "value", None), state_ctx, item)
    rendered = registry.render_component(item.component_name, props=props, state=state_ctx.state_snapshot())
    element_id = _element_id(page_slug, "custom_component", path)
    index = path[-1] if path else 0
    base = _base_element(element_id, page_name, page_slug, index, item)
    element = {
        **base,
        "type": "custom_component",
        "component": item.component_name,
        "plugin": item.plugin_name,
        "props": props,
        "nodes": rendered,
    }
    return element, {}


def _resolve_component_prop_value(value: object, state_ctx: StateContext, item: ir.PageItem) -> object:
    if isinstance(value, ir.StatePath):
        label = f"state.{'.'.join(value.path)}"
        if not state_ctx.has_value(value.path):
            raise Namel3ssError(
                f"Custom component property requires known state path '{label}'.",
                line=getattr(item, "line", None),
                column=getattr(item, "column", None),
            )
        try:
            resolved, _ = state_ctx.value(value.path, default=None, register_default=False)
            return resolved
        except KeyError as err:
            raise Namel3ssError(
                f"Custom component property requires known state path '{label}'.",
                line=getattr(item, "line", None),
                column=getattr(item, "column", None),
            ) from err
    if isinstance(value, ir.Literal):
        return value.value
    return value


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
    parent_visible: bool,
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
            build_children=_build_children,
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
        element, actions = _build_custom_component_element(
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
            build_children=_build_children,
            parent_visible=effective_visible,
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
            build_children=_build_children,
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
            build_children=_build_children,
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
            build_children=_build_children,
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
            build_children=_build_children,
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
            build_children=_build_children,
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
            build_children=_build_children,
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
            build_children=_build_children,
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
            build_children=_build_children,
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


__all__ = ["_build_children"]
