from __future__ import annotations

from typing import List

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.parser.core.helpers import parse_reference_name

_ALLOWED_MEMORY_LANES = {"my", "team", "system"}


def parse_chat_block(parser) -> List[ast.PageItem]:
    parser._expect("NEWLINE", "Expected newline after chat")
    parser._expect("INDENT", "Expected indented chat block")
    items: List[ast.PageItem] = []
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        tok = parser._current()
        if tok.type == "IDENT" and tok.value == "messages":
            items.append(_parse_messages(parser))
            continue
        if tok.type == "IDENT" and tok.value == "composer":
            items.append(_parse_composer(parser))
            continue
        if tok.type == "IDENT" and tok.value == "thinking":
            items.append(_parse_thinking(parser))
            continue
        if tok.type == "IDENT" and tok.value == "citations":
            items.append(_parse_citations(parser))
            continue
        if tok.type == "MEMORY" or (tok.type == "IDENT" and tok.value == "memory"):
            items.append(_parse_memory(parser))
            continue
        raise Namel3ssError("Chat blocks may only contain messages, composer, thinking, citations, or memory", line=tok.line, column=tok.column)
    parser._expect("DEDENT", "Expected end of chat block")
    if not items:
        tok = parser._current()
        raise Namel3ssError("Chat block has no entries", line=tok.line, column=tok.column)
    return items


def _parse_messages(parser) -> ast.ChatMessagesItem:
    tok = parser._advance()
    from_tok = parser._current()
    if from_tok.type != "IDENT" or from_tok.value != "from":
        raise Namel3ssError("Messages must use: messages from is state.<path>", line=from_tok.line, column=from_tok.column)
    parser._advance()
    parser._expect("IS", "Expected 'is' after messages from")
    source = parser._parse_state_path()
    parser._match("NEWLINE")
    return ast.ChatMessagesItem(source=source, line=tok.line, column=tok.column)


def _parse_composer(parser) -> ast.ChatComposerItem:
    tok = parser._advance()
    parser._expect("CALLS", "Expected 'calls' after composer")
    parser._expect("FLOW", "Expected 'flow' keyword after composer calls")
    flow_name = parse_reference_name(parser, context="flow")
    parser._match("NEWLINE")
    return ast.ChatComposerItem(flow_name=flow_name, line=tok.line, column=tok.column)


def _parse_thinking(parser) -> ast.ChatThinkingItem:
    tok = parser._advance()
    parser._expect("WHEN", "Expected 'when' after thinking")
    parser._expect("IS", "Expected 'is' after thinking when")
    when = parser._parse_state_path()
    parser._match("NEWLINE")
    return ast.ChatThinkingItem(when=when, line=tok.line, column=tok.column)


def _parse_citations(parser) -> ast.ChatCitationsItem:
    tok = parser._advance()
    from_tok = parser._current()
    if from_tok.type != "IDENT" or from_tok.value != "from":
        raise Namel3ssError("Citations must use: citations from is state.<path>", line=from_tok.line, column=from_tok.column)
    parser._advance()
    parser._expect("IS", "Expected 'is' after citations from")
    source = parser._parse_state_path()
    parser._match("NEWLINE")
    return ast.ChatCitationsItem(source=source, line=tok.line, column=tok.column)


def _parse_memory(parser) -> ast.ChatMemoryItem:
    tok = parser._advance()
    from_tok = parser._current()
    if from_tok.type != "IDENT" or from_tok.value != "from":
        raise Namel3ssError("Memory must use: memory from is state.<path>", line=from_tok.line, column=from_tok.column)
    parser._advance()
    parser._expect("IS", "Expected 'is' after memory from")
    source = parser._parse_state_path()
    lane = None
    if parser._current().type == "IDENT" and parser._current().value == "lane":
        parser._advance()
        parser._expect("IS", "Expected 'is' after lane")
        value_tok = parser._current()
        if value_tok.type not in {"STRING", "IDENT"}:
            raise Namel3ssError("Lane must be 'my', 'team', or 'system'", line=value_tok.line, column=value_tok.column)
        parser._advance()
        lane = str(value_tok.value).lower()
        if lane not in _ALLOWED_MEMORY_LANES:
            raise Namel3ssError("Lane must be 'my', 'team', or 'system'", line=value_tok.line, column=value_tok.column)
    parser._match("NEWLINE")
    return ast.ChatMemoryItem(source=source, lane=lane, line=tok.line, column=tok.column)


__all__ = ["parse_chat_block"]
