from __future__ import annotations

import copy

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.ir.lowering.ui_patterns_values import (
    qualify_name,
    resolve_boolean_optional,
    resolve_number_optional,
    resolve_page,
    resolve_record,
    resolve_record_optional,
    resolve_state,
    resolve_state_optional,
    resolve_text,
    resolve_text_optional,
    resolve_visibility,
    resolve_visibility_rule,
)


def materialize_item(
    item: ast.PageItem,
    *,
    flow_names: set[str],
    page_names: set[str],
    record_names: set[str],
    context_module: str | None,
    param_values: dict[str, object] | None,
    param_defs: dict[str, ast.PatternParam] | None,
) -> ast.PageItem | None:
    working = copy.deepcopy(item)
    working.visibility = resolve_visibility(working.visibility, param_values=param_values, param_defs=param_defs)
    working.visibility_rule = resolve_visibility_rule(working.visibility_rule, param_values=param_values, param_defs=param_defs)
    if isinstance(working, ast.TitleItem):
        value = resolve_text(working.value, param_values=param_values, param_defs=param_defs)
        if value is None:
            return None
        working.value = value
        return working
    if isinstance(working, ast.TextItem):
        value = resolve_text(working.value, param_values=param_values, param_defs=param_defs)
        if value is None:
            return None
        working.value = value
        return working
    if isinstance(working, ast.TextInputItem):
        name = resolve_text(working.name, param_values=param_values, param_defs=param_defs)
        flow = resolve_text(working.flow_name, param_values=param_values, param_defs=param_defs)
        if name is None or flow is None:
            return None
        working.name = name
        working.flow_name = qualify_name(flow, context_module, flow_names)
        return working
    if isinstance(working, ast.ImageItem):
        src = resolve_text(working.src, param_values=param_values, param_defs=param_defs)
        if src is None:
            return None
        working.src = src
        working.role = resolve_text_optional(working.role, param_values=param_values, param_defs=param_defs)
        return working
    if isinstance(working, ast.UploadItem):
        name = resolve_text(working.name, param_values=param_values, param_defs=param_defs)
        if name is None:
            return None
        working.name = name
        working.multiple = resolve_boolean_optional(working.multiple, param_values=param_values, param_defs=param_defs)
        return working
    if isinstance(working, ast.ViewItem):
        record = resolve_record(working.record_name, param_values=param_values, param_defs=param_defs)
        if record is None:
            return None
        working.record_name = qualify_name(record, context_module, record_names)
        return working
    if isinstance(working, ast.FormItem):
        record = resolve_record(working.record_name, param_values=param_values, param_defs=param_defs)
        if record is None:
            return None
        working.record_name = qualify_name(record, context_module, record_names)
        working.groups = resolve_form_groups(working.groups, param_values=param_values, param_defs=param_defs)
        working.fields = resolve_form_fields(working.fields, param_values=param_values, param_defs=param_defs)
        return working
    if isinstance(working, ast.TableItem):
        record = resolve_record_optional(working.record_name, param_values=param_values, param_defs=param_defs)
        source = resolve_state_optional(working.source, param_values=param_values, param_defs=param_defs)
        if record is None and source is None:
            return None
        if record is not None:
            record = qualify_name(record, context_module, record_names)
        working.record_name = record
        working.source = source
        working.empty_text = resolve_text_optional(working.empty_text, param_values=param_values, param_defs=param_defs)
        working.row_actions = resolve_row_actions(
            working.row_actions,
            param_values=param_values,
            param_defs=param_defs,
            context_module=context_module,
            flow_names=flow_names,
        )
        working.pagination = resolve_pagination(working.pagination, param_values=param_values, param_defs=param_defs)
        return working
    if isinstance(working, ast.ListItem):
        record = resolve_record_optional(working.record_name, param_values=param_values, param_defs=param_defs)
        source = resolve_state_optional(working.source, param_values=param_values, param_defs=param_defs)
        if record is None and source is None:
            return None
        if record is not None:
            record = qualify_name(record, context_module, record_names)
        working.record_name = record
        working.source = source
        working.empty_text = resolve_text_optional(working.empty_text, param_values=param_values, param_defs=param_defs)
        working.actions = resolve_list_actions(
            working.actions,
            param_values=param_values,
            param_defs=param_defs,
            context_module=context_module,
            flow_names=flow_names,
        )
        return working
    if isinstance(working, ast.ChartItem):
        record = resolve_record_optional(working.record_name, param_values=param_values, param_defs=param_defs)
        source = resolve_state_optional(working.source, param_values=param_values, param_defs=param_defs)
        if record is None and source is None:
            return None
        if record is not None:
            record = qualify_name(record, context_module, record_names)
        working.record_name = record
        working.source = source
        working.explain = resolve_text_optional(working.explain, param_values=param_values, param_defs=param_defs)
        return working
    if isinstance(working, ast.ButtonItem):
        label = resolve_text(working.label, param_values=param_values, param_defs=param_defs)
        flow = resolve_text(working.flow_name, param_values=param_values, param_defs=param_defs)
        if label is None or flow is None:
            return None
        working.label = label
        working.flow_name = qualify_name(flow, context_module, flow_names)
        return working
    if isinstance(working, ast.LinkItem):
        label = resolve_text(working.label, param_values=param_values, param_defs=param_defs)
        target = resolve_page(working.page_name, param_values=param_values, param_defs=param_defs)
        if label is None or target is None:
            return None
        working.label = label
        working.page_name = qualify_name(target, context_module, page_names)
        return working
    if isinstance(working, ast.ChatMessagesItem):
        source = resolve_state(working.source, param_values=param_values, param_defs=param_defs)
        if source is None:
            return None
        working.source = source
        return working
    if isinstance(working, ast.ChatComposerItem):
        flow = resolve_text(working.flow_name, param_values=param_values, param_defs=param_defs)
        if flow is None:
            return None
        working.flow_name = qualify_name(flow, context_module, flow_names)
        return working
    if isinstance(working, ast.ChatThinkingItem):
        when = resolve_state(working.when, param_values=param_values, param_defs=param_defs)
        if when is None:
            return None
        working.when = when
        return working
    if isinstance(working, ast.ChatCitationsItem):
        source = resolve_state(working.source, param_values=param_values, param_defs=param_defs)
        if source is None:
            return None
        working.source = source
        return working
    if isinstance(working, ast.ChatMemoryItem):
        source = resolve_state(working.source, param_values=param_values, param_defs=param_defs)
        if source is None:
            return None
        working.source = source
        return working
    if isinstance(working, ast.NumberItem):
        entries: list[ast.NumberEntry] = []
        for entry in working.entries:
            next_entry = copy.deepcopy(entry)
            if next_entry.kind == "count":
                record = resolve_record(next_entry.record_name, param_values=param_values, param_defs=param_defs)
                label = resolve_text(next_entry.label, param_values=param_values, param_defs=param_defs)
                if record is None or label is None:
                    continue
                next_entry.record_name = qualify_name(record, context_module, record_names)
                next_entry.label = label
            entries.append(next_entry)
        if not entries:
            return None
        working.entries = entries
        return working
    if isinstance(working, ast.StoryItem):
        title = resolve_text(working.title, param_values=param_values, param_defs=param_defs)
        if title is None:
            return None
        steps: list[ast.StoryStep] = []
        for step in working.steps:
            next_step = copy.deepcopy(step)
            step_title = resolve_text(next_step.title, param_values=param_values, param_defs=param_defs)
            if step_title is None:
                continue
            next_step.title = step_title
            next_step.text = resolve_text_optional(next_step.text, param_values=param_values, param_defs=param_defs)
            next_step.image = resolve_text_optional(next_step.image, param_values=param_values, param_defs=param_defs)
            next_step.tone = resolve_text_optional(next_step.tone, param_values=param_values, param_defs=param_defs)
            next_step.requires = resolve_text_optional(next_step.requires, param_values=param_values, param_defs=param_defs)
            next_step.next = resolve_text_optional(next_step.next, param_values=param_values, param_defs=param_defs)
            steps.append(next_step)
        if not steps:
            return None
        working.title = title
        working.steps = steps
        return working
    if isinstance(working, ast.SectionItem):
        working.label = resolve_text_optional(working.label, param_values=param_values, param_defs=param_defs)
        return working
    if isinstance(working, ast.CardItem):
        working.label = resolve_text_optional(working.label, param_values=param_values, param_defs=param_defs)
        working.actions = resolve_card_actions(
            working.actions,
            param_values=param_values,
            param_defs=param_defs,
            context_module=context_module,
            flow_names=flow_names,
        )
        return working
    if isinstance(working, (ast.ModalItem, ast.DrawerItem)):
        label = resolve_text(working.label, param_values=param_values, param_defs=param_defs)
        if label is None:
            return None
        working.label = label
        return working
    if isinstance(working, ast.CustomComponentItem):
        resolved_props: list[ast.CustomComponentProp] = []
        for prop in list(working.properties):
            next_prop = copy.deepcopy(prop)
            value = next_prop.value
            if isinstance(value, ast.PatternParamRef):
                resolved = resolve_param_ref(
                    value,
                    expected_kinds={"text", "number", "boolean", "state"},
                    param_values=param_values,
                    param_defs=param_defs,
                )
                next_prop.value = resolved
            resolved_props.append(next_prop)
        working.properties = resolved_props
        return working
    return working


def materialize_tab(
    tab: ast.TabItem,
    *,
    param_values: dict[str, object] | None,
    param_defs: dict[str, ast.PatternParam] | None,
) -> ast.TabItem | None:
    working = copy.deepcopy(tab)
    working.visibility = resolve_visibility(working.visibility, param_values=param_values, param_defs=param_defs)
    return working


def resolve_form_groups(
    groups: list[ast.FormGroup] | None,
    *,
    param_values: dict[str, object] | None,
    param_defs: dict[str, ast.PatternParam] | None,
) -> list[ast.FormGroup] | None:
    if groups is None:
        return None
    resolved: list[ast.FormGroup] = []
    for group in groups:
        next_group = copy.deepcopy(group)
        label = resolve_text(next_group.label, param_values=param_values, param_defs=param_defs)
        if label is None:
            continue
        next_group.label = label
        resolved.append(next_group)
    return resolved or None


def resolve_form_fields(
    fields: list[ast.FormFieldConfig] | None,
    *,
    param_values: dict[str, object] | None,
    param_defs: dict[str, ast.PatternParam] | None,
) -> list[ast.FormFieldConfig] | None:
    if fields is None:
        return None
    resolved: list[ast.FormFieldConfig] = []
    for field in fields:
        next_field = copy.deepcopy(field)
        next_field.help = resolve_text_optional(next_field.help, param_values=param_values, param_defs=param_defs)
        next_field.readonly = resolve_boolean_optional(next_field.readonly, param_values=param_values, param_defs=param_defs)
        if next_field.help is None and next_field.readonly is None:
            continue
        resolved.append(next_field)
    return resolved or None


def resolve_row_actions(
    actions: list[ast.TableRowAction] | None,
    *,
    param_values: dict[str, object] | None,
    param_defs: dict[str, ast.PatternParam] | None,
    context_module: str | None,
    flow_names: set[str],
) -> list[ast.TableRowAction] | None:
    if not actions:
        return None
    resolved: list[ast.TableRowAction] = []
    for action in actions:
        next_action = copy.deepcopy(action)
        label = resolve_text(next_action.label, param_values=param_values, param_defs=param_defs)
        if label is None:
            continue
        next_action.label = label
        if next_action.kind == "call_flow":
            flow = resolve_text(next_action.flow_name, param_values=param_values, param_defs=param_defs)
            if flow is None:
                continue
            next_action.flow_name = qualify_name(flow, context_module, flow_names)
        else:
            target = resolve_text(next_action.target, param_values=param_values, param_defs=param_defs)
            if target is None:
                continue
            next_action.target = target
        resolved.append(next_action)
    return resolved or None


def resolve_list_actions(
    actions: list[ast.ListAction] | None,
    *,
    param_values: dict[str, object] | None,
    param_defs: dict[str, ast.PatternParam] | None,
    context_module: str | None,
    flow_names: set[str],
) -> list[ast.ListAction] | None:
    if not actions:
        return None
    resolved: list[ast.ListAction] = []
    for action in actions:
        next_action = copy.deepcopy(action)
        label = resolve_text(next_action.label, param_values=param_values, param_defs=param_defs)
        if label is None:
            continue
        next_action.label = label
        if next_action.kind == "call_flow":
            flow = resolve_text(next_action.flow_name, param_values=param_values, param_defs=param_defs)
            if flow is None:
                continue
            next_action.flow_name = qualify_name(flow, context_module, flow_names)
        else:
            target = resolve_text(next_action.target, param_values=param_values, param_defs=param_defs)
            if target is None:
                continue
            next_action.target = target
        resolved.append(next_action)
    return resolved or None


def resolve_card_actions(
    actions: list[ast.CardAction] | None,
    *,
    param_values: dict[str, object] | None,
    param_defs: dict[str, ast.PatternParam] | None,
    context_module: str | None,
    flow_names: set[str],
) -> list[ast.CardAction] | None:
    if not actions:
        return None
    resolved: list[ast.CardAction] = []
    for action in actions:
        next_action = copy.deepcopy(action)
        if next_action.kind == "call_flow":
            flow = resolve_text(next_action.flow_name, param_values=param_values, param_defs=param_defs)
            if flow is None:
                continue
            next_action.flow_name = qualify_name(flow, context_module, flow_names)
        else:
            target = resolve_text(next_action.target, param_values=param_values, param_defs=param_defs)
            if target is None:
                continue
            next_action.target = target
        resolved.append(next_action)
    return resolved or None


def resolve_pagination(
    pagination: ast.TablePagination | None,
    *,
    param_values: dict[str, object] | None,
    param_defs: dict[str, ast.PatternParam] | None,
) -> ast.TablePagination | None:
    if pagination is None:
        return None
    next_pagination = copy.deepcopy(pagination)
    page_size = resolve_number_optional(next_pagination.page_size, param_values=param_values, param_defs=param_defs)
    if page_size is None:
        return None
    if page_size <= 0 or int(page_size) != page_size:
        raise Namel3ssError("page_size must be a positive integer", line=pagination.line, column=pagination.column)
    next_pagination.page_size = int(page_size)
    return next_pagination


__all__ = [
    "materialize_item",
    "materialize_tab",
    "resolve_form_fields",
    "resolve_form_groups",
    "resolve_list_actions",
    "resolve_pagination",
    "resolve_row_actions",
]
