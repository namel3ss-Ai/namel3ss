from __future__ import annotations

import difflib

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.lang.types import CANONICAL_TYPES, canonicalize_type_name
from namel3ss.parser.core.helpers import parse_reference_name
from namel3ss.parser.decl.record import _FIELD_NAME_TOKENS, type_from_token


_DECLARATIVE_STEPS = ("input", "require", "create", "update", "delete", "call foreign")
_IMPERATIVE_HINTS = {
    "LET": "let",
    "SET": "set",
    "RETURN": "return",
    "IF": "if",
    "MATCH": "match",
    "REPEAT": "repeat",
    "FOR": "for each",
    "TRY": "try",
    "ASK": "ask",
    "RUN": "run",
    "PARALLEL": "parallel",
    "ORCHESTRATION": "orchestration",
    "FIND": "find",
    "SAVE": "save",
}


def parse_flow_steps(parser) -> list[ast.FlowStep]:
    steps: list[ast.FlowStep] = []
    saw_input = False
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        tok = parser._current()
        if tok.type == "INPUT" or (tok.type == "IDENT" and tok.value == "input"):
            if saw_input:
                raise Namel3ssError(
                    build_guidance_message(
                        what="Flow declares input more than once.",
                        why="Declarative flows may only declare a single input block.",
                        fix="Combine the input fields into one input block.",
                        example='flow "demo"\\n  input\\n    name is text',
                    ),
                    line=tok.line,
                    column=tok.column,
                )
            steps.append(_parse_input(parser))
            saw_input = True
            continue
        if tok.type == "REQUIRE" or (tok.type == "IDENT" and tok.value == "require"):
            steps.append(_parse_require(parser))
            continue
        if tok.type == "CALL" or (tok.type == "IDENT" and tok.value == "call"):
            steps.append(_parse_call_foreign(parser))
            continue
        if tok.type == "CREATE":
            steps.append(_parse_create(parser))
            continue
        if tok.type == "IDENT" and tok.value == "update":
            steps.append(_parse_update(parser))
            continue
        if tok.type == "IDENT" and tok.value == "delete":
            steps.append(_parse_delete(parser))
            continue
        _raise_unknown_step(tok)
    return steps


def _parse_input(parser) -> ast.FlowInput:
    tok = parser._advance()
    parser._expect("NEWLINE", "Expected newline after input")
    parser._expect("INDENT", "Expected indented input block")
    fields: list[ast.FlowInputField] = []
    seen: set[str] = set()
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        name_tok = parser._current()
        if name_tok.type not in _FIELD_NAME_TOKENS:
            raise Namel3ssError(
                build_guidance_message(
                    what="Input fields must start with a field name.",
                    why="Input blocks declare one field per line: <name> is <type>.",
                    fix="Use an unquoted field name followed by `is` and a type.",
                    example='input\\n  name is text',
                ),
                line=name_tok.line,
                column=name_tok.column,
            )
        parser._advance()
        field_name = name_tok.value
        parser._expect("IS", "Expected 'is' after input field name")
        type_tok = parser._current()
        raw_type = None
        if type_tok.type == "TEXT":
            raw_type = "text"
            parser._advance()
        elif type_tok.type.startswith("TYPE_"):
            parser._advance()
            raw_type = type_from_token(type_tok)
        else:
            raise Namel3ssError("Expected input field type", line=type_tok.line, column=type_tok.column)
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
                f"Unsupported input field type '{canonical_type}'",
                line=type_tok.line,
                column=type_tok.column,
            )
        if field_name in seen:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Input field '{field_name}' is duplicated.",
                    why="Input fields must be unique.",
                    fix="Remove the duplicate or rename it.",
                    example='input\\n  name is text\\n  email is text',
                ),
                line=name_tok.line,
                column=name_tok.column,
            )
        seen.add(field_name)
        fields.append(
            ast.FlowInputField(
                name=field_name,
                type_name=canonical_type,
                type_was_alias=type_was_alias,
                raw_type_name=raw_type if type_was_alias else None,
                type_line=type_tok.line,
                type_column=type_tok.column,
                line=name_tok.line,
                column=name_tok.column,
            )
        )
        parser._match("NEWLINE")
    parser._expect("DEDENT", "Expected end of input block")
    while parser._match("NEWLINE"):
        pass
    if not fields:
        raise Namel3ssError(
            build_guidance_message(
                what="Input block has no fields.",
                why="Input blocks must declare at least one field.",
                fix="Add one or more fields under input.",
                example='input\\n  name is text',
            ),
            line=tok.line,
            column=tok.column,
        )
    return ast.FlowInput(fields=fields, line=tok.line, column=tok.column)


def _parse_require(parser) -> ast.FlowRequire:
    tok = parser._advance()
    cond_tok = parser._expect("STRING", "Expected requires condition string")
    parser._match("NEWLINE")
    return ast.FlowRequire(condition=cond_tok.value, line=tok.line, column=tok.column)


def _parse_call_foreign(parser) -> ast.FlowCallForeign:
    tok = parser._advance()
    foreign_tok = parser._current()
    if not _match_word(parser, "IDENT", "foreign"):
        raise Namel3ssError(
            build_guidance_message(
                what="Call step must be 'call foreign'.",
                why="Declarative flows only allow foreign calls in call steps.",
                fix='Use `call foreign "<name>"`.',
                example='call foreign "calculate tax"\\n  amount is input.amount',
            ),
            line=foreign_tok.line,
            column=foreign_tok.column,
        )
    name_tok = parser._expect("STRING", "Expected foreign function name string")
    parser._expect("NEWLINE", "Expected newline after call foreign header")
    if not parser._match("INDENT"):
        return ast.FlowCallForeign(foreign_name=name_tok.value, arguments=[], line=tok.line, column=tok.column)
    arguments = _parse_field_block(parser, section="call foreign")
    parser._expect("DEDENT", "Expected end of call foreign block")
    while parser._match("NEWLINE"):
        pass
    return ast.FlowCallForeign(
        foreign_name=name_tok.value,
        arguments=arguments,
        line=tok.line,
        column=tok.column,
    )


def _parse_create(parser) -> ast.FlowCreate:
    tok = parser._advance()
    record_name = parse_reference_name(parser, context="record")
    parser._expect("NEWLINE", "Expected newline after create header")
    parser._expect("INDENT", "Expected indented create block")
    fields = _parse_field_block(parser, section="create")
    parser._expect("DEDENT", "Expected end of create block")
    while parser._match("NEWLINE"):
        pass
    if not fields:
        raise Namel3ssError(
            build_guidance_message(
                what="Create step has no field assignments.",
                why="Create requires at least one field assignment.",
                fix="Add one or more field assignments under create.",
                example='create "Order"\\n  status is "new"',
            ),
            line=tok.line,
            column=tok.column,
        )
    return ast.FlowCreate(record_name=record_name, fields=fields, line=tok.line, column=tok.column)


def _parse_update(parser) -> ast.FlowUpdate:
    tok = parser._advance()
    record_name = parse_reference_name(parser, context="record")
    parser._expect("NEWLINE", "Expected newline after update header")
    parser._expect("INDENT", "Expected indented update block")
    selector: str | None = None
    updates: list[ast.FlowField] | None = None
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        if _match_word(parser, "WHERE", "where"):
            if selector is not None:
                raise Namel3ssError(
                    build_guidance_message(
                        what="Update step declares where more than once.",
                        why="Declarative update steps only allow one selector.",
                        fix="Keep a single where line.",
                        example='update "Order"\\n  where "id is 1"\\n  set\\n    status is "shipped"',
                    ),
                    line=tok.line,
                    column=tok.column,
                )
            selector_tok = parser._expect("STRING", "Expected selector string after where")
            selector = selector_tok.value
            parser._match("NEWLINE")
            continue
        if _match_word(parser, "SET", "set"):
            if updates is not None:
                raise Namel3ssError(
                    build_guidance_message(
                        what="Update step declares set more than once.",
                        why="Update assignments belong in a single set block.",
                        fix="Keep one set block with all assignments.",
                        example='update "Order"\\n  set\\n    status is "shipped"',
                    ),
                    line=tok.line,
                    column=tok.column,
                )
            parser._expect("NEWLINE", "Expected newline after set")
            parser._expect("INDENT", "Expected indented set block")
            updates = _parse_field_block(parser, section="set")
            parser._expect("DEDENT", "Expected end of set block")
            continue
        tok_item = parser._current()
        raise Namel3ssError(
            build_guidance_message(
                what="Update step entries must be where or set.",
                why="Declarative updates use an optional where selector and a set block.",
                fix='Add `where "<selector>"` or `set` with assignments.',
                example='update "Order"\\n  where "id is 1"\\n  set\\n    status is "shipped"',
            ),
            line=tok_item.line,
            column=tok_item.column,
        )
    parser._expect("DEDENT", "Expected end of update block")
    while parser._match("NEWLINE"):
        pass
    if updates is None:
        raise Namel3ssError(
            build_guidance_message(
                what="Update step is missing a set block.",
                why="Update assignments must be declared under set.",
                fix="Add a set block with one or more assignments.",
                example='update "Order"\\n  set\\n    status is "shipped"',
            ),
            line=tok.line,
            column=tok.column,
        )
    if not updates:
        raise Namel3ssError(
            build_guidance_message(
                what="Update step has no assignments.",
                why="Update requires at least one field assignment.",
                fix="Add one or more field assignments under set.",
                example='update "Order"\\n  set\\n    status is "shipped"',
            ),
            line=tok.line,
            column=tok.column,
        )
    return ast.FlowUpdate(
        record_name=record_name,
        selector=selector,
        updates=updates,
        line=tok.line,
        column=tok.column,
    )


def _parse_delete(parser) -> ast.FlowDelete:
    tok = parser._advance()
    record_name = parse_reference_name(parser, context="record")
    parser._expect("NEWLINE", "Expected newline after delete header")
    parser._expect("INDENT", "Expected indented delete block")
    selector: str | None = None
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        if _match_word(parser, "WHERE", "where"):
            if selector is not None:
                raise Namel3ssError(
                    build_guidance_message(
                        what="Delete step declares where more than once.",
                        why="Declarative delete steps only allow one selector.",
                        fix="Keep a single where line.",
                        example='delete "Order"\\n  where "id is 1"',
                    ),
                    line=tok.line,
                    column=tok.column,
                )
            selector_tok = parser._expect("STRING", "Expected selector string after where")
            selector = selector_tok.value
            parser._match("NEWLINE")
            continue
        tok_item = parser._current()
        raise Namel3ssError(
            build_guidance_message(
                what="Delete step entries must be where.",
                why="Declarative deletes use a where selector.",
                fix='Add `where "<selector>"`.',
                example='delete "Order"\\n  where "id is 1"',
            ),
            line=tok_item.line,
            column=tok_item.column,
        )
    parser._expect("DEDENT", "Expected end of delete block")
    while parser._match("NEWLINE"):
        pass
    return ast.FlowDelete(record_name=record_name, selector=selector, line=tok.line, column=tok.column)


def _parse_field_block(parser, *, section: str) -> list[ast.FlowField]:
    fields: list[ast.FlowField] = []
    seen: set[str] = set()
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        name_tok = parser._current()
        if name_tok.type != "IDENT":
            raise Namel3ssError(
                build_guidance_message(
                    what=f"{section.title()} assignments must start with a field name.",
                    why="Assignments use <field> is <value>.",
                    fix="Use an unquoted field name followed by `is` and a value.",
                    example='name is "example"',
                ),
                line=name_tok.line,
                column=name_tok.column,
            )
        parser._advance()
        field_name = name_tok.value
        parser._expect("IS", "Expected 'is' after field name")
        expr = parser._parse_expression()
        if field_name in seen:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Field '{field_name}' is duplicated.",
                    why="Each field may only be assigned once per step.",
                    fix="Remove the duplicate assignment.",
                    example=f'{field_name} is "value"',
                ),
                line=name_tok.line,
                column=name_tok.column,
            )
        seen.add(field_name)
        fields.append(ast.FlowField(name=field_name, value=expr, line=name_tok.line, column=name_tok.column))
        parser._match("NEWLINE")
    return fields


def _raise_unknown_step(tok) -> None:
    value = tok.value if isinstance(tok.value, str) else tok.type.lower()
    hint = _IMPERATIVE_HINTS.get(tok.type)
    if tok.type == "IDENT" and tok.value in _IMPERATIVE_HINTS.values():
        hint = tok.value
    if hint:
        raise Namel3ssError(
            build_guidance_message(
                what=f"Declarative flows do not support '{hint}' steps.",
                why="Declarative flows only allow input, require, create, update, delete, and call foreign.",
                fix='Use a legacy flow with ":" for imperative statements or rewrite the flow steps.',
                example='flow "demo":\\n  let count is 1',
            ),
            line=tok.line,
            column=tok.column,
        )
    suggestion = difflib.get_close_matches(str(value), _DECLARATIVE_STEPS, n=1, cutoff=0.6)
    suggestion_text = f" Did you mean '{suggestion[0]}'?" if suggestion else ""
    raise Namel3ssError(
        build_guidance_message(
            what=f"Unknown flow step '{value}'.{suggestion_text}",
            why="Declarative flows only allow input, require, create, update, delete, and call foreign.",
            fix="Use one of the supported steps.",
            example='flow "demo"\\n  input\\n    name is text',
        ),
        line=tok.line,
        column=tok.column,
    )


def _match_word(parser, token_type: str, value: str) -> bool:
    tok = parser._current()
    if tok.type == token_type:
        parser._advance()
        return True
    if tok.type == "IDENT" and tok.value == value:
        parser._advance()
        return True
    return False


__all__ = ["parse_flow_steps"]
