from __future__ import annotations

import difflib

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.ir.lowering.expressions import _lower_expression
from namel3ss.ir.model.expressions import Literal as IRLiteral
from namel3ss.ir.model.expressions import StatePath as IRStatePath
from namel3ss.ir.model.pages import VisibilityRule as IRVisibilityRule
from namel3ss.schema import records as schema

from . import actions as actions_mod
from . import media as media_mod
from . import numbers as numbers_mod
from . import story as story_mod
from . import views as views_mod


def _attach_origin(target, source):
    origin = getattr(source, "origin", None)
    if origin is not None:
        setattr(target, "origin", origin)
    visibility = _lower_visibility(source)
    if visibility is not None:
        setattr(target, "visibility", visibility)
    visibility_rule = _lower_visibility_rule(source)
    if visibility_rule is not None:
        setattr(target, "visibility_rule", visibility_rule)
    return target


def _lower_visibility(source) -> IRStatePath | None:
    visibility = getattr(source, "visibility", None)
    if visibility is None:
        return None
    if not isinstance(visibility, ast.StatePath):
        raise Namel3ssError(
            "Visibility requires state.<path>.",
            line=getattr(source, "line", None),
            column=getattr(source, "column", None),
        )
    lowered = _lower_expression(visibility)
    if not isinstance(lowered, IRStatePath):
        raise Namel3ssError(
            "Visibility requires state.<path>.",
            line=getattr(source, "line", None),
            column=getattr(source, "column", None),
        )
    return lowered


def _lower_visibility_rule(source) -> IRVisibilityRule | None:
    rule = getattr(source, "visibility_rule", None)
    if rule is None:
        return None
    if not isinstance(rule, ast.VisibilityRule):
        raise Namel3ssError(
            "Visibility rule requires state.<path> is <value>.",
            line=getattr(source, "line", None),
            column=getattr(source, "column", None),
        )
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


def _unknown_record_message(name: str, record_map: dict[str, schema.RecordSchema]) -> str:
    suggestion = difflib.get_close_matches(name, record_map.keys(), n=1, cutoff=0.6)
    hint = f' Did you mean "{suggestion[0]}"?' if suggestion else ""
    return f"Page references unknown record '{name}'.{hint}"


def _unknown_page_message(name: str, page_names: set[str]) -> str:
    suggestion = difflib.get_close_matches(name, page_names, n=1, cutoff=0.6)
    hint = f' Did you mean "{suggestion[0]}"?' if suggestion else ""
    return f"Page references unknown page '{name}'.{hint}"


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
    if isinstance(item, ast.UploadItem):
        return views_mod.lower_upload_item(item, attach_origin=_attach_origin)
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
    if isinstance(item, ast.ChartItem):
        return views_mod.lower_chart_item(item, record_map, page_name, attach_origin=_attach_origin)
    if isinstance(item, ast.ChatItem):
        return views_mod.lower_chat_item(item, flow_names, page_name, attach_origin=_attach_origin)
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
    raise TypeError(f"Unhandled page item type: {type(item)}")


__all__ = ["_lower_page_item"]
