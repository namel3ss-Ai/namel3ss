from __future__ import annotations

from typing import List

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.parser.decl.page_common import (
    _parse_reference_name_value,
    _parse_state_path_value,
    _parse_string_value,
    _parse_visibility_clause,
)

_ALLOWED_MEMORY_LANES = {"my", "team", "system"}


def parse_chat_block(parser, *, allow_pattern_params: bool = False) -> List[ast.PageItem]:
    parser._expect("NEWLINE", "Expected newline after chat")
    parser._expect("INDENT", "Expected indented chat block")
    items: List[ast.PageItem] = []
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        tok = parser._current()
        if tok.type == "IDENT" and tok.value == "messages":
            items.append(_parse_messages(parser, allow_pattern_params=allow_pattern_params))
            continue
        if tok.type == "IDENT" and tok.value == "composer":
            items.append(_parse_composer(parser, allow_pattern_params=allow_pattern_params))
            continue
        if tok.type == "IDENT" and tok.value == "thinking":
            items.append(_parse_thinking(parser, allow_pattern_params=allow_pattern_params))
            continue
        if tok.type == "IDENT" and tok.value == "citations":
            items.append(_parse_citations(parser, allow_pattern_params=allow_pattern_params))
            continue
        if tok.type == "MEMORY" or (tok.type == "IDENT" and tok.value == "memory"):
            items.append(_parse_memory(parser, allow_pattern_params=allow_pattern_params))
            continue
        raise Namel3ssError("Chat blocks may only contain messages, composer, thinking, citations, or memory", line=tok.line, column=tok.column)
    parser._expect("DEDENT", "Expected end of chat block")
    if not items:
        tok = parser._current()
        raise Namel3ssError("Chat block has no entries", line=tok.line, column=tok.column)
    return items


def _parse_messages(parser, *, allow_pattern_params: bool) -> ast.ChatMessagesItem:
    tok = parser._advance()
    from_tok = parser._current()
    if from_tok.type != "IDENT" or from_tok.value != "from":
        raise Namel3ssError("Messages must use: messages from is state.<path>", line=from_tok.line, column=from_tok.column)
    parser._advance()
    parser._expect("IS", "Expected 'is' after messages from")
    source = _parse_state_path_value(parser, allow_pattern_params=allow_pattern_params)
    visibility = _parse_visibility_clause(parser, allow_pattern_params=allow_pattern_params)
    parser._match("NEWLINE")
    return ast.ChatMessagesItem(source=source, visibility=visibility, line=tok.line, column=tok.column)


def _parse_composer(parser, *, allow_pattern_params: bool) -> ast.ChatComposerItem:
    tok = parser._advance()
    parser._expect("CALLS", "Expected 'calls' after composer")
    parser._expect("FLOW", "Expected 'flow' keyword after composer calls")
    flow_name = _parse_reference_name_value(parser, allow_pattern_params=allow_pattern_params, context="flow")
    visibility = _parse_visibility_clause(parser, allow_pattern_params=allow_pattern_params)
    parser._match("NEWLINE")
    return ast.ChatComposerItem(flow_name=flow_name, visibility=visibility, line=tok.line, column=tok.column)


def _parse_thinking(parser, *, allow_pattern_params: bool) -> ast.ChatThinkingItem:
    tok = parser._advance()
    parser._expect("WHEN", "Expected 'when' after thinking")
    parser._expect("IS", "Expected 'is' after thinking when")
    when = _parse_state_path_value(parser, allow_pattern_params=allow_pattern_params)
    visibility = _parse_visibility_clause(parser, allow_pattern_params=allow_pattern_params)
    parser._match("NEWLINE")
    return ast.ChatThinkingItem(when=when, visibility=visibility, line=tok.line, column=tok.column)


def _parse_citations(parser, *, allow_pattern_params: bool) -> ast.ChatCitationsItem:
    tok = parser._advance()
    from_tok = parser._current()
    if from_tok.type != "IDENT" or from_tok.value != "from":
        raise Namel3ssError("Citations must use: citations from is state.<path>", line=from_tok.line, column=from_tok.column)
    parser._advance()
    parser._expect("IS", "Expected 'is' after citations from")
    source = _parse_state_path_value(parser, allow_pattern_params=allow_pattern_params)
    visibility = _parse_visibility_clause(parser, allow_pattern_params=allow_pattern_params)
    parser._match("NEWLINE")
    return ast.ChatCitationsItem(source=source, visibility=visibility, line=tok.line, column=tok.column)


def _parse_memory(parser, *, allow_pattern_params: bool) -> ast.ChatMemoryItem:
    tok = parser._advance()
    from_tok = parser._current()
    if from_tok.type != "IDENT" or from_tok.value != "from":
        raise Namel3ssError("Memory must use: memory from is state.<path>", line=from_tok.line, column=from_tok.column)
    parser._advance()
    parser._expect("IS", "Expected 'is' after memory from")
    source = _parse_state_path_value(parser, allow_pattern_params=allow_pattern_params)
    lane = None
    if parser._current().type == "IDENT" and parser._current().value == "lane":
        parser._advance()
        parser._expect("IS", "Expected 'is' after lane")
        value_tok = parser._current()
        if value_tok.type not in {"STRING", "IDENT"}:
            raise Namel3ssError("Lane must be 'my', 'team', or 'system'", line=value_tok.line, column=value_tok.column)
        if value_tok.type == "STRING":
            parser._advance()
            lane = value_tok.value
        else:
            lane = _parse_string_value(parser, allow_pattern_params=allow_pattern_params, context="lane")
        lane = str(lane).lower()
        if lane not in _ALLOWED_MEMORY_LANES:
            raise Namel3ssError("Lane must be 'my', 'team', or 'system'", line=value_tok.line, column=value_tok.column)
    visibility = _parse_visibility_clause(parser, allow_pattern_params=allow_pattern_params)
    parser._match("NEWLINE")
    return ast.ChatMemoryItem(source=source, lane=lane, visibility=visibility, line=tok.line, column=tok.column)


__all__ = ["parse_chat_block"]
