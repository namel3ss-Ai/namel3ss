from __future__ import annotations

from typing import List

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.lang.types import CANONICAL_TYPES, canonicalize_type_name
from namel3ss.parser.decl.page_common import (
    _is_visibility_rule_start,
    _parse_reference_name_value,
    _parse_state_path_value,
    _parse_string_value,
    _parse_visibility_clause,
    _parse_visibility_rule_block,
    _parse_visibility_rule_line,
    _validate_visibility_combo,
)
from namel3ss.parser.decl.record import _FIELD_NAME_TOKENS, type_from_token

_ALLOWED_MEMORY_LANES = {"my", "team", "system"}


def parse_chat_block(parser, *, allow_pattern_params: bool = False) -> tuple[List[ast.PageItem], ast.VisibilityRule | None]:
    parser._expect("NEWLINE", "Expected newline after chat")
    parser._expect("INDENT", "Expected indented chat block")
    items: List[ast.PageItem] = []
    visibility_rule: ast.VisibilityRule | None = None
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        tok = parser._current()
        if _is_visibility_rule_start(parser):
            if visibility_rule is not None:
                raise Namel3ssError("Visibility blocks may only declare one only-when rule.", line=tok.line, column=tok.column)
            visibility_rule = _parse_visibility_rule_line(parser, allow_pattern_params=allow_pattern_params)
            parser._match("NEWLINE")
            continue
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
    return items, visibility_rule


def _parse_messages(parser, *, allow_pattern_params: bool) -> ast.ChatMessagesItem:
    tok = parser._advance()
    from_tok = parser._current()
    if from_tok.type != "IDENT" or from_tok.value != "from":
        raise Namel3ssError("Messages must use: messages from is state.<path>", line=from_tok.line, column=from_tok.column)
    parser._advance()
    parser._expect("IS", "Expected 'is' after messages from")
    source = _parse_state_path_value(parser, allow_pattern_params=allow_pattern_params)
    visibility = _parse_visibility_clause(parser, allow_pattern_params=allow_pattern_params)
    visibility_rule = _parse_visibility_rule_block(parser, allow_pattern_params=allow_pattern_params)
    _validate_visibility_combo(visibility, visibility_rule, line=tok.line, column=tok.column)
    parser._match("NEWLINE")
    return ast.ChatMessagesItem(
        source=source,
        visibility=visibility,
        visibility_rule=visibility_rule,
        line=tok.line,
        column=tok.column,
    )


def _parse_composer(parser, *, allow_pattern_params: bool) -> ast.ChatComposerItem:
    tok = parser._advance()
    uses_calls = False
    if parser._match("CALLS"):
        uses_calls = True
        parser._expect("FLOW", "Expected 'flow' keyword after composer calls")
        flow_name = _parse_reference_name_value(parser, allow_pattern_params=allow_pattern_params, context="flow")
    else:
        action_tok = parser._current()
        if action_tok.type == "IDENT" and action_tok.value == "sends":
            parser._advance()
            parser._expect("TO", "Expected 'to' after sends")
            parser._expect("FLOW", "Expected 'flow' after sends to")
            flow_name = _parse_reference_name_value(parser, allow_pattern_params=allow_pattern_params, context="flow")
        else:
            raise Namel3ssError(
                'Composer must use: composer calls flow "<name>" or composer sends to flow "<name>"',
                line=action_tok.line,
                column=action_tok.column,
            )
    visibility = _parse_visibility_clause(parser, allow_pattern_params=allow_pattern_params)
    fields: list[ast.ChatComposerField] = []
    visibility_rule = None
    if parser._match("NEWLINE"):
        if parser._match("INDENT"):
            fields, visibility_rule = _parse_composer_fields(parser, allow_pattern_params=allow_pattern_params)
            if uses_calls and fields:
                raise Namel3ssError(
                    'Structured composers must use: composer sends to flow "<name>"',
                    line=tok.line,
                    column=tok.column,
                )
    _validate_visibility_combo(visibility, visibility_rule, line=tok.line, column=tok.column)
    return ast.ChatComposerItem(
        flow_name=flow_name,
        fields=fields,
        visibility=visibility,
        visibility_rule=visibility_rule,
        line=tok.line,
        column=tok.column,
    )


def _parse_composer_fields(parser, *, allow_pattern_params: bool) -> tuple[list[ast.ChatComposerField], ast.VisibilityRule | None]:
    fields: list[ast.ChatComposerField] = []
    seen: set[str] = set()
    visibility_rule: ast.VisibilityRule | None = None
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        if _is_visibility_rule_start(parser):
            if visibility_rule is not None:
                tok = parser._current()
                raise Namel3ssError(
                    "Visibility blocks may only declare one only-when rule.",
                    line=tok.line,
                    column=tok.column,
                )
            visibility_rule = _parse_visibility_rule_line(parser, allow_pattern_params=allow_pattern_params)
            parser._match("NEWLINE")
            continue
        tok = parser._current()
        if tok.type == "IDENT" and tok.value == "send":
            parser._advance()
            field = _parse_composer_field(parser, allow_pattern_params=allow_pattern_params)
            _register_composer_field(field, seen)
            fields.append(field)
            parser._match("NEWLINE")
            if parser._match("INDENT"):
                _parse_composer_field_block(parser, fields, seen, allow_pattern_params=allow_pattern_params)
            continue
        raise Namel3ssError(
            'Composer fields must use: send <name> as <type>',
            line=tok.line,
            column=tok.column,
        )
    parser._expect("DEDENT", "Expected end of composer block")
    if not fields and visibility_rule is None:
        tok = parser._current()
        raise Namel3ssError("Composer block has no fields", line=tok.line, column=tok.column)
    return fields, visibility_rule


def _parse_composer_field_block(
    parser,
    fields: list[ast.ChatComposerField],
    seen: set[str],
    *,
    allow_pattern_params: bool,
) -> None:
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        tok = parser._current()
        if tok.type == "IDENT" and tok.value == "send":
            raise Namel3ssError(
                "Remove 'send' from nested composer fields; indentation already implies send.",
                line=tok.line,
                column=tok.column,
            )
        field = _parse_composer_field(parser, allow_pattern_params=allow_pattern_params)
        _register_composer_field(field, seen)
        fields.append(field)
        parser._match("NEWLINE")
    parser._expect("DEDENT", "Expected end of send block")


def _parse_composer_field(parser, *, allow_pattern_params: bool) -> ast.ChatComposerField:
    name_tok = parser._current()
    if name_tok.type not in _FIELD_NAME_TOKENS:
        raise Namel3ssError(
            "Composer fields must start with a field name",
            line=name_tok.line,
            column=name_tok.column,
        )
    parser._advance()
    field_name = name_tok.value
    parser._expect("AS", "Expected 'as' after composer field name")
    type_tok = parser._current()
    raw_type = None
    if type_tok.type == "TEXT":
        raw_type = "text"
        parser._advance()
    elif type_tok.type.startswith("TYPE_"):
        parser._advance()
        raw_type = type_from_token(type_tok)
    else:
        raise Namel3ssError("Expected composer field type", line=type_tok.line, column=type_tok.column)
    canonical_type, type_was_alias = canonicalize_type_name(raw_type)
    if type_was_alias and not getattr(parser, "allow_legacy_type_aliases", True):
        raise Namel3ssError(
            f"N3PARSER_TYPE_ALIAS_DISALLOWED: Type alias '{raw_type}' is not allowed. Use '{canonical_type}'. "
            "Fix: run `n3 app.ai format` to rewrite aliases.",
            line=type_tok.line,
            column=type_tok.column,
        )
    if canonical_type not in CANONICAL_TYPES:
        raise Namel3ssError(
            f"Unsupported composer field type '{canonical_type}'",
            line=type_tok.line,
            column=type_tok.column,
        )
    if canonical_type != "text":
        raise Namel3ssError(
            "Composer fields must be text",
            line=type_tok.line,
            column=type_tok.column,
        )
    return ast.ChatComposerField(
        name=field_name,
        type_name=canonical_type,
        type_was_alias=type_was_alias,
        raw_type_name=raw_type if type_was_alias else None,
        type_line=type_tok.line,
        type_column=type_tok.column,
        line=name_tok.line,
        column=name_tok.column,
    )


def _register_composer_field(field: ast.ChatComposerField, seen: set[str]) -> None:
    name = field.name
    if name == "message":
        raise Namel3ssError(
            "Composer fields must not shadow 'message'",
            line=field.line,
            column=field.column,
        )
    if name in seen:
        raise Namel3ssError(
            f"Composer field '{name}' is duplicated",
            line=field.line,
            column=field.column,
        )
    seen.add(name)


def _parse_thinking(parser, *, allow_pattern_params: bool) -> ast.ChatThinkingItem:
    tok = parser._advance()
    parser._expect("WHEN", "Expected 'when' after thinking")
    parser._expect("IS", "Expected 'is' after thinking when")
    when = _parse_state_path_value(parser, allow_pattern_params=allow_pattern_params)
    visibility = _parse_visibility_clause(parser, allow_pattern_params=allow_pattern_params)
    visibility_rule = _parse_visibility_rule_block(parser, allow_pattern_params=allow_pattern_params)
    _validate_visibility_combo(visibility, visibility_rule, line=tok.line, column=tok.column)
    parser._match("NEWLINE")
    return ast.ChatThinkingItem(
        when=when,
        visibility=visibility,
        visibility_rule=visibility_rule,
        line=tok.line,
        column=tok.column,
    )


def _parse_citations(parser, *, allow_pattern_params: bool) -> ast.ChatCitationsItem:
    tok = parser._advance()
    from_tok = parser._current()
    if from_tok.type != "IDENT" or from_tok.value != "from":
        raise Namel3ssError("Citations must use: citations from is state.<path>", line=from_tok.line, column=from_tok.column)
    parser._advance()
    parser._expect("IS", "Expected 'is' after citations from")
    source = _parse_state_path_value(parser, allow_pattern_params=allow_pattern_params)
    visibility = _parse_visibility_clause(parser, allow_pattern_params=allow_pattern_params)
    visibility_rule = _parse_visibility_rule_block(parser, allow_pattern_params=allow_pattern_params)
    _validate_visibility_combo(visibility, visibility_rule, line=tok.line, column=tok.column)
    parser._match("NEWLINE")
    return ast.ChatCitationsItem(
        source=source,
        visibility=visibility,
        visibility_rule=visibility_rule,
        line=tok.line,
        column=tok.column,
    )


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
    visibility_rule = _parse_visibility_rule_block(parser, allow_pattern_params=allow_pattern_params)
    _validate_visibility_combo(visibility, visibility_rule, line=tok.line, column=tok.column)
    parser._match("NEWLINE")
    return ast.ChatMemoryItem(
        source=source,
        lane=lane,
        visibility=visibility,
        visibility_rule=visibility_rule,
        line=tok.line,
        column=tok.column,
    )


__all__ = ["parse_chat_block"]
