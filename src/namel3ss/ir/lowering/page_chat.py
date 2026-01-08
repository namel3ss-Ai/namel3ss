from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir
from namel3ss.ir.lowering.expressions import _lower_expression

_ALLOWED_MEMORY_LANES = {"my", "team", "system"}


def _lower_chat_item(item: ast.ChatItem, flow_names: set[str], page_name: str) -> ir.ChatItem:
    children = [_lower_chat_child(child, flow_names, page_name) for child in item.children]
    if not children:
        raise Namel3ssError("Chat block has no entries", line=item.line, column=item.column)
    return ir.ChatItem(children=children, line=item.line, column=item.column)


def _lower_chat_child(child: ast.PageItem, flow_names: set[str], page_name: str) -> ir.PageItem:
    if isinstance(child, ast.ChatMessagesItem):
        source = _lower_expression(child.source)
        if not isinstance(source, ir.StatePath):
            raise Namel3ssError("Messages must bind to state.<path>", line=child.line, column=child.column)
        return ir.ChatMessagesItem(source=source, line=child.line, column=child.column)
    if isinstance(child, ast.ChatComposerItem):
        if child.flow_name not in flow_names:
            raise Namel3ssError(
                f"Page '{page_name}' references unknown flow '{child.flow_name}'",
                line=child.line,
                column=child.column,
            )
        return ir.ChatComposerItem(flow_name=child.flow_name, line=child.line, column=child.column)
    if isinstance(child, ast.ChatThinkingItem):
        when = _lower_expression(child.when)
        if not isinstance(when, ir.StatePath):
            raise Namel3ssError("Thinking must bind to state.<path>", line=child.line, column=child.column)
        return ir.ChatThinkingItem(when=when, line=child.line, column=child.column)
    if isinstance(child, ast.ChatCitationsItem):
        source = _lower_expression(child.source)
        if not isinstance(source, ir.StatePath):
            raise Namel3ssError("Citations must bind to state.<path>", line=child.line, column=child.column)
        return ir.ChatCitationsItem(source=source, line=child.line, column=child.column)
    if isinstance(child, ast.ChatMemoryItem):
        source = _lower_expression(child.source)
        if not isinstance(source, ir.StatePath):
            raise Namel3ssError("Memory must bind to state.<path>", line=child.line, column=child.column)
        lane = child.lane
        if lane is not None and lane not in _ALLOWED_MEMORY_LANES:
            raise Namel3ssError("Memory lane must be 'my', 'team', or 'system'", line=child.line, column=child.column)
        return ir.ChatMemoryItem(source=source, lane=lane, line=child.line, column=child.column)
    raise Namel3ssError("Chat blocks may only contain messages, composer, thinking, citations, or memory", line=child.line, column=child.column)


__all__ = ["_lower_chat_item"]
