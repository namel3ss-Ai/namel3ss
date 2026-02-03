from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir
from namel3ss.ir.lowering.expressions import _lower_expression
from namel3ss.ir.lowering.flow_refs import unknown_flow_message

_ALLOWED_MEMORY_LANES = {"my", "team", "system"}


def _lower_chat_item(item: ast.ChatItem, flow_names: set[str], page_name: str, *, attach_origin) -> ir.ChatItem:
    children = [_lower_chat_child(child, flow_names, page_name, attach_origin=attach_origin) for child in item.children]
    if not children:
        raise Namel3ssError("Chat block has no entries", line=item.line, column=item.column)
    return ir.ChatItem(children=children, line=item.line, column=item.column)


def _lower_chat_child(child: ast.PageItem, flow_names: set[str], page_name: str, *, attach_origin) -> ir.PageItem:
    if isinstance(child, ast.ChatMessagesItem):
        source = _lower_expression(child.source)
        if not isinstance(source, ir.StatePath):
            raise Namel3ssError("Messages must bind to state.<path>", line=child.line, column=child.column)
        return attach_origin(ir.ChatMessagesItem(source=source, line=child.line, column=child.column), child)
    if isinstance(child, ast.ChatComposerItem):
        if child.flow_name not in flow_names:
            raise Namel3ssError(
                unknown_flow_message(child.flow_name, flow_names, page_name),
                line=child.line,
                column=child.column,
            )
        fields = [
            ir.ChatComposerField(
                name=field.name,
                type_name=field.type_name,
                type_was_alias=field.type_was_alias,
                raw_type_name=field.raw_type_name,
                type_line=field.type_line,
                type_column=field.type_column,
                line=field.line,
                column=field.column,
            )
            for field in (child.fields or [])
        ]
        return attach_origin(
            ir.ChatComposerItem(flow_name=child.flow_name, fields=fields, line=child.line, column=child.column),
            child,
        )
    if isinstance(child, ast.ChatThinkingItem):
        when = _lower_expression(child.when)
        if not isinstance(when, ir.StatePath):
            raise Namel3ssError("Thinking must bind to state.<path>", line=child.line, column=child.column)
        return attach_origin(ir.ChatThinkingItem(when=when, line=child.line, column=child.column), child)
    if isinstance(child, ast.ChatCitationsItem):
        source = _lower_expression(child.source)
        if not isinstance(source, ir.StatePath):
            raise Namel3ssError("Citations must bind to state.<path>", line=child.line, column=child.column)
        return attach_origin(ir.ChatCitationsItem(source=source, line=child.line, column=child.column), child)
    if isinstance(child, ast.ChatMemoryItem):
        source = _lower_expression(child.source)
        if not isinstance(source, ir.StatePath):
            raise Namel3ssError("Memory must bind to state.<path>", line=child.line, column=child.column)
        lane = child.lane
        if lane is not None and lane not in _ALLOWED_MEMORY_LANES:
            raise Namel3ssError("Memory lane must be 'my', 'team', or 'system'", line=child.line, column=child.column)
        return attach_origin(ir.ChatMemoryItem(source=source, lane=lane, line=child.line, column=child.column), child)
    raise Namel3ssError("Chat blocks may only contain messages, composer, thinking, citations, or memory", line=child.line, column=child.column)


__all__ = ["_lower_chat_item"]
