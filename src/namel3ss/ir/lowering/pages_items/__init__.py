from __future__ import annotations

import difflib

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.ir.lowering.expressions import _lower_expression
from namel3ss.ir.model.base import Expression as IRExpression
from namel3ss.ir.model.expressions import Literal as IRLiteral
from namel3ss.ir.model.expressions import StatePath as IRStatePath
from namel3ss.ir.model.pages import CustomComponentItem as IRCustomComponentItem
from namel3ss.ir.model.pages import CustomComponentProp as IRCustomComponentProp
from namel3ss.ir.model.pages import ThemeSettingsPageItem
from namel3ss.ir.model.pages import VisibilityExpressionRule as IRVisibilityExpressionRule
from namel3ss.ir.model.pages import VisibilityRule as IRVisibilityRule
from namel3ss.ir.lowering.page_rag import (
    _lower_citation_chips_item,
    _lower_scope_selector_item,
    _lower_source_preview_item,
    _lower_trust_indicator_item,
)
from namel3ss.ir.lowering.page_tokens import lower_theme_overrides
from namel3ss.ir.lowering.ui_slider_lower import lower_slider_item
from namel3ss.ir.lowering.ui_tooltip_lower import lower_tooltip_item
from namel3ss.ir.lowering import page_layout as layout_mod
from namel3ss.schema import records as schema
from namel3ss.ui.theme import normalize_style_hooks, normalize_variant

from . import actions as actions_mod
from . import media as media_mod
from . import numbers as numbers_mod
from . import polish as polish_mod
from . import story as story_mod
from . import views as views_mod

_PLUGIN_REGISTRY = None


def set_plugin_registry(registry) -> None:
    global _PLUGIN_REGISTRY
    _PLUGIN_REGISTRY = registry


def _attach_origin(target, source):
    origin = getattr(source, "origin", None)
    if origin is not None:
        setattr(target, "origin", origin)
    visibility = _lower_visibility(source)
    if visibility is not None:
        setattr(target, "visibility", visibility)
    show_when = _lower_show_when(source)
    if show_when is not None:
        setattr(target, "show_when", show_when)
    visibility_rule = _lower_visibility_rule(source)
    if visibility_rule is not None:
        setattr(target, "visibility_rule", visibility_rule)
    debug_only = getattr(source, "debug_only", None)
    if debug_only is not None:
        setattr(target, "debug_only", debug_only)
    theme_overrides = lower_theme_overrides(getattr(source, "theme_overrides", None))
    if theme_overrides is not None:
        setattr(target, "theme_overrides", theme_overrides)
    component = _style_component_name(source)
    if component:
        variant = normalize_variant(
            component,
            getattr(source, "variant", None),
            line=getattr(source, "line", None),
            column=getattr(source, "column", None),
        )
        if variant is not None:
            setattr(target, "variant", variant)
        style_hooks = normalize_style_hooks(
            component,
            getattr(source, "style_hooks", None),
            line=getattr(source, "line", None),
            column=getattr(source, "column", None),
        )
        if style_hooks is not None:
            setattr(target, "style_hooks", style_hooks)
    return target


def _style_component_name(source) -> str | None:
    name = type(source).__name__.lower()
    if "button" in name:
        return "button"
    if "carditem" in name or name == "card":
        return "card"
    return None


def _lower_visibility(source) -> IRExpression | None:
    visibility = getattr(source, "visibility", None)
    if visibility is None:
        return None
    if isinstance(visibility, ast.PatternParamRef):
        raise Namel3ssError(
            "Visibility expressions cannot use unresolved pattern parameters.",
            line=getattr(source, "line", None),
            column=getattr(source, "column", None),
        )
    lowered = _lower_expression(visibility)
    if not isinstance(lowered, IRExpression):
        raise Namel3ssError(
            "Visibility requires a deterministic expression.",
            line=getattr(source, "line", None),
            column=getattr(source, "column", None),
        )
    return lowered


def _lower_show_when(source) -> IRExpression | None:
    show_when = getattr(source, "show_when", None)
    if show_when is None:
        return None
    if isinstance(show_when, ast.PatternParamRef):
        raise Namel3ssError(
            "show_when expressions cannot use unresolved pattern parameters.",
            line=getattr(source, "line", None),
            column=getattr(source, "column", None),
        )
    lowered = _lower_expression(show_when)
    if not isinstance(lowered, IRExpression):
        raise Namel3ssError(
            "show_when requires a deterministic expression.",
            line=getattr(source, "line", None),
            column=getattr(source, "column", None),
        )
    return lowered


def _lower_visibility_rule(source) -> IRVisibilityRule | IRVisibilityExpressionRule | None:
    rule = getattr(source, "visibility_rule", None)
    if rule is None:
        return None
    if isinstance(rule, ast.VisibilityExpressionRule):
        lowered_expr = _lower_expression(rule.expression)
        if not isinstance(lowered_expr, IRExpression):
            raise Namel3ssError(
                "Visibility expressions require deterministic operands.",
                line=getattr(rule, "line", None),
                column=getattr(rule, "column", None),
            )
        return IRVisibilityExpressionRule(expression=lowered_expr, line=rule.line, column=rule.column)
    if isinstance(rule, ast.VisibilityRule):
        lowered_path = _lower_expression(rule.path)
        if not isinstance(lowered_path, IRStatePath):
            raise Namel3ssError(
                "Visibility rule requires state.<path> is <value>.",
                line=getattr(rule, "line", None),
                column=getattr(rule, "column", None),
            )
        lowered_value = _lower_expression(rule.value)
        if not isinstance(lowered_value, IRLiteral):
            raise Namel3ssError(
                "Visibility rule requires a text, number, or boolean literal.",
                line=getattr(rule.value, "line", None),
                column=getattr(rule.value, "column", None),
            )
        return IRVisibilityRule(path=lowered_path, value=lowered_value, line=rule.line, column=rule.column)
    raise Namel3ssError(
        "Visibility rule requires either an expression or state.<path> is <value>.",
        line=getattr(source, "line", None),
        column=getattr(source, "column", None),
    )


def _unknown_record_message(name: str, record_map: dict[str, schema.RecordSchema]) -> str:
    suggestion = difflib.get_close_matches(name, record_map.keys(), n=1, cutoff=0.6)
    hint = f' Did you mean "{suggestion[0]}"?' if suggestion else ""
    return f"Page references unknown record '{name}'.{hint}"


def _unknown_page_message(name: str, page_names: set[str]) -> str:
    suggestion = difflib.get_close_matches(name, page_names, n=1, cutoff=0.6)
    hint = f' Did you mean "{suggestion[0]}"?' if suggestion else ""
    return f"Page references unknown page '{name}'.{hint}"


def _lower_custom_component_item(
    item: ast.CustomComponentItem,
    flow_names: set[str],
) -> IRCustomComponentItem:
    if _PLUGIN_REGISTRY is None:
        raise Namel3ssError(
            "Custom UI component registry is not initialized.",
            line=item.line,
            column=item.column,
        )
    plugin_name, normalized = _PLUGIN_REGISTRY.validate_component_usage(
        item.component_name,
        list(item.properties),
        flow_names,
        line=item.line,
        column=item.column,
    )
    properties: list[IRCustomComponentProp] = []
    for name, value in normalized:
        lowered_value = _lower_expression(value) if isinstance(value, ast.Expression) else value
        properties.append(IRCustomComponentProp(name=name, value=lowered_value, line=item.line, column=item.column))
    lowered = IRCustomComponentItem(
        component_name=item.component_name,
        plugin_name=plugin_name,
        properties=properties,
        line=item.line,
        column=item.column,
    )
    return _attach_origin(lowered, item)


def _lower_page_item(
    item: ast.PageItem,
    record_map: dict[str, schema.RecordSchema],
    flow_names: set[str],
    page_name: str,
    page_names: set[str],
    overlays: dict[str, set[str]],
    compose_names: set[str] | None = None,
):
    compose_names = compose_names if compose_names is not None else set()
    if isinstance(item, ast.NumberItem):
        return numbers_mod.lower_number_item(
            item,
            record_map,
            attach_origin=_attach_origin,
            unknown_record_message=_unknown_record_message,
        )
    if isinstance(item, ast.ViewItem):
        return views_mod.lower_view_item(
            item,
            record_map,
            attach_origin=_attach_origin,
            unknown_record_message=_unknown_record_message,
        )
    if isinstance(item, ast.ComposeItem):
        return actions_mod.lower_compose_item(
            item,
            record_map,
            flow_names,
            page_name,
            page_names,
            overlays,
            compose_names,
            lower_page_item=_lower_page_item,
            attach_origin=_attach_origin,
        )
    if isinstance(item, ast.StoryItem):
        return story_mod.lower_story_item(item, attach_origin=_attach_origin)
    if isinstance(item, ast.TitleItem):
        return actions_mod.lower_title_item(item, attach_origin=_attach_origin)
    if isinstance(item, ast.TextItem):
        return actions_mod.lower_text_item(item, attach_origin=_attach_origin)
    if isinstance(item, ast.TextInputItem):
        return actions_mod.lower_text_input_item(
            item,
            flow_names,
            page_name,
            attach_origin=_attach_origin,
        )
    if isinstance(item, ast.SliderItem):
        return lower_slider_item(
            item,
            flow_names,
            page_name,
            attach_origin=_attach_origin,
        )
    if isinstance(item, ast.TooltipItem):
        return lower_tooltip_item(
            item,
            attach_origin=_attach_origin,
        )
    if isinstance(item, ast.UploadItem):
        return views_mod.lower_upload_item(item, attach_origin=_attach_origin)
    if isinstance(item, ast.LoadingItem):
        return polish_mod.lower_loading_item(item, attach_origin=_attach_origin)
    if isinstance(item, ast.SnackbarItem):
        return polish_mod.lower_snackbar_item(item, attach_origin=_attach_origin)
    if isinstance(item, ast.IconItem):
        return polish_mod.lower_icon_item(item, attach_origin=_attach_origin)
    if isinstance(item, ast.LightboxItem):
        return polish_mod.lower_lightbox_item(item, attach_origin=_attach_origin)
    if isinstance(item, ast.FormItem):
        return views_mod.lower_form_item(
            item,
            record_map,
            page_name,
            attach_origin=_attach_origin,
        )
    if isinstance(item, ast.TableItem):
        return views_mod.lower_table_item(
            item,
            record_map,
            flow_names,
            page_name,
            page_names,
            overlays,
            attach_origin=_attach_origin,
        )
    if isinstance(item, ast.ListItem):
        return views_mod.lower_list_item(
            item,
            record_map,
            flow_names,
            page_name,
            page_names,
            overlays,
            attach_origin=_attach_origin,
        )
    if isinstance(item, ast.ThemeSettingsPageItem):
        return _attach_origin(ThemeSettingsPageItem(line=item.line, column=item.column), item)
    if isinstance(item, ast.ChartItem):
        return views_mod.lower_chart_item(item, record_map, page_name, attach_origin=_attach_origin)
    if isinstance(item, ast.ChatItem):
        return views_mod.lower_chat_item(item, flow_names, page_name, attach_origin=_attach_origin)
    if isinstance(item, ast.CitationChipsItem):
        return _lower_citation_chips_item(item, attach_origin=_attach_origin)
    if isinstance(item, ast.SourcePreviewItem):
        return _lower_source_preview_item(item, attach_origin=_attach_origin)
    if isinstance(item, ast.TrustIndicatorItem):
        return _lower_trust_indicator_item(item, attach_origin=_attach_origin)
    if isinstance(item, ast.ScopeSelectorItem):
        return _lower_scope_selector_item(item, attach_origin=_attach_origin)
    if isinstance(item, ast.CustomComponentItem):
        return _lower_custom_component_item(item, flow_names)
    if isinstance(item, ast.TabsItem):
        return views_mod.lower_tabs_item(
            item,
            record_map,
            flow_names,
            page_name,
            page_names,
            overlays,
            compose_names,
            lower_page_item=_lower_page_item,
            attach_origin=_attach_origin,
        )
    if isinstance(item, ast.ButtonItem):
        return actions_mod.lower_button_item(
            item,
            flow_names,
            page_name,
            page_names,
            attach_origin=_attach_origin,
        )
    if isinstance(item, ast.LinkItem):
        return actions_mod.lower_link_item(
            item,
            page_names,
            attach_origin=_attach_origin,
            unknown_page_message=_unknown_page_message,
        )
    if isinstance(item, ast.SectionItem):
        return actions_mod.lower_section_item(
            item,
            record_map,
            flow_names,
            page_name,
            page_names,
            overlays,
            compose_names,
            lower_page_item=_lower_page_item,
            attach_origin=_attach_origin,
        )
    if isinstance(item, ast.CardGroupItem):
        return actions_mod.lower_card_group_item(
            item,
            record_map,
            flow_names,
            page_name,
            page_names,
            overlays,
            compose_names,
            lower_page_item=_lower_page_item,
            attach_origin=_attach_origin,
        )
    if isinstance(item, ast.CardItem):
        return actions_mod.lower_card_item(
            item,
            record_map,
            flow_names,
            page_name,
            page_names,
            overlays,
            compose_names,
            lower_page_item=_lower_page_item,
            attach_origin=_attach_origin,
        )
    if isinstance(item, ast.RowItem):
        return actions_mod.lower_row_item(
            item,
            record_map,
            flow_names,
            page_name,
            page_names,
            overlays,
            compose_names,
            lower_page_item=_lower_page_item,
            attach_origin=_attach_origin,
        )
    if isinstance(item, ast.ColumnItem):
        return actions_mod.lower_column_item(
            item,
            record_map,
            flow_names,
            page_name,
            page_names,
            overlays,
            compose_names,
            lower_page_item=_lower_page_item,
            attach_origin=_attach_origin,
        )
    if isinstance(item, ast.GridItem):
        return polish_mod.lower_grid_item(
            item,
            record_map,
            flow_names,
            page_name,
            page_names,
            overlays,
            compose_names,
            lower_page_item=_lower_page_item,
            attach_origin=_attach_origin,
        )
    if isinstance(item, ast.DividerItem):
        return actions_mod.lower_divider_item(item, attach_origin=_attach_origin)
    if isinstance(item, ast.ImageItem):
        return media_mod.lower_image_item(item, attach_origin=_attach_origin)
    if isinstance(item, ast.ModalItem):
        return actions_mod.lower_modal_item(
            item,
            record_map,
            flow_names,
            page_name,
            page_names,
            overlays,
            compose_names,
            lower_page_item=_lower_page_item,
            attach_origin=_attach_origin,
        )
    if isinstance(item, ast.DrawerItem):
        return actions_mod.lower_drawer_item(
            item,
            record_map,
            flow_names,
            page_name,
            page_names,
            overlays,
            compose_names,
            lower_page_item=_lower_page_item,
            attach_origin=_attach_origin,
        )
    layout_item = layout_mod.lower_layout_item(
        item,
        record_map,
        flow_names,
        page_name,
        page_names,
        overlays,
        compose_names,
        lower_page_item=_lower_page_item,
        attach_origin=_attach_origin,
    )
    if layout_item is not None:
        return layout_item
    raise TypeError(f"Unhandled page item type: {type(item)}")


__all__ = ["_lower_page_item", "set_plugin_registry"]
