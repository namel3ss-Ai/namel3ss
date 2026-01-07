from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.lang.types import canonicalize_type_name
from namel3ss.parser.decl.record import type_from_token
from namel3ss.utils.numbers import decimal_is_int, is_number, to_decimal


_SUPPORTED_FIELD_TYPES = {"text", "number", "boolean", "json", "list", "map"}


def parse_tool(parser) -> ast.ToolDecl:
    tool_tok = parser._advance()
    name_tok = parser._expect("STRING", "Expected tool name string")
    parser._expect("COLON", "Expected ':' after tool name")
    parser._expect("NEWLINE", "Expected newline after tool header")
    parser._expect("INDENT", "Expected indented tool body")

    kind = None
    purity = "impure"
    timeout_seconds = None
    input_fields = None
    output_fields = None

    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        tok = parser._current()
        if tok.type in {"KIND", "ENTRY", "INPUT_SCHEMA", "OUTPUT_SCHEMA"}:
            raise Namel3ssError(_old_tool_syntax_message(), line=tok.line, column=tok.column)
        if _match_word(parser, "implemented"):
            _expect_word(parser, "using")
            if kind is not None:
                raise Namel3ssError("Tool implementation is declared more than once", line=tok.line, column=tok.column)
            kind_tok = parser._current()
            if not isinstance(kind_tok.value, str):
                raise Namel3ssError(
                    "Expected implementation kind after 'implemented using'",
                    line=kind_tok.line,
                    column=kind_tok.column,
                )
            parser._advance()
            kind = kind_tok.value.strip().lower()
            parser._match("NEWLINE")
            continue
        if _is_word(tok, "input"):
            if input_fields is not None:
                raise Namel3ssError("Tool input is declared more than once", line=tok.line, column=tok.column)
            input_fields = _parse_tool_fields_block(parser, section_name="input")
            continue
        if _is_word(tok, "output"):
            if output_fields is not None:
                raise Namel3ssError("Tool output is declared more than once", line=tok.line, column=tok.column)
            output_fields = _parse_tool_fields_block(parser, section_name="output")
            continue
        if tok.type == "PURITY":
            parser._advance()
            parser._expect("IS", "Expected 'is' after purity")
            value_tok = parser._current()
            if not isinstance(value_tok.value, str):
                raise Namel3ssError("Expected purity string", line=value_tok.line, column=value_tok.column)
            parser._advance()
            purity = value_tok.value.strip().lower()
            if purity not in {"pure", "impure"}:
                raise Namel3ssError("purity must be 'pure' or 'impure'", line=value_tok.line, column=value_tok.column)
            parser._match("NEWLINE")
            continue
        if tok.type == "TIMEOUT_SECONDS":
            parser._advance()
            parser._expect("IS", "Expected 'is' after timeout_seconds")
            value_tok = parser._expect("NUMBER", "timeout_seconds must be a number literal")
            if not is_number(value_tok.value):
                raise Namel3ssError(
                    "timeout_seconds must be a positive integer",
                    line=value_tok.line,
                    column=value_tok.column,
                )
            value_decimal = to_decimal(value_tok.value)
            if not decimal_is_int(value_decimal) or value_decimal <= 0:
                raise Namel3ssError(
                    "timeout_seconds must be a positive integer",
                    line=value_tok.line,
                    column=value_tok.column,
                )
            timeout_seconds = int(value_decimal)
            parser._match("NEWLINE")
            continue
        raise Namel3ssError("Unknown field in tool declaration", line=tok.line, column=tok.column)
    parser._expect("DEDENT", "Expected end of tool body")

    if kind is None:
        raise Namel3ssError(
            build_guidance_message(
                what=f'Tool "{name_tok.value}" is missing implementation.',
                why="Tools must declare how they are implemented.",
                fix="Add an implementation line like `implemented using python`.",
                example=_tool_decl_example(name_tok.value),
            ),
            line=tool_tok.line,
            column=tool_tok.column,
        )
    if input_fields is None:
        raise Namel3ssError(
            build_guidance_message(
                what=f'Tool "{name_tok.value}" is missing an input section.',
                why="Tools must declare input fields for validation.",
                fix="Add an input: block with field names and types.",
                example=_tool_decl_example(name_tok.value),
            ),
            line=tool_tok.line,
            column=tool_tok.column,
        )
    if output_fields is None:
        raise Namel3ssError(
            build_guidance_message(
                what=f'Tool "{name_tok.value}" is missing an output section.',
                why="Tools must declare output fields for validation.",
                fix="Add an output: block with field names and types.",
                example=_tool_decl_example(name_tok.value),
            ),
            line=tool_tok.line,
            column=tool_tok.column,
        )

    return ast.ToolDecl(
        name=name_tok.value,
        kind=kind,
        input_fields=input_fields,
        output_fields=output_fields,
        purity=purity,
        timeout_seconds=timeout_seconds,
        line=tool_tok.line,
        column=tool_tok.column,
    )


def _parse_tool_fields_block(parser, *, section_name: str) -> list[ast.ToolField]:
    parser._advance()
    parser._expect("COLON", f"Expected ':' after {section_name}")
    parser._expect("NEWLINE", f"Expected newline after {section_name}:")
    if not parser._match("INDENT"):
        return []
    fields: list[ast.ToolField] = []
    seen = set()
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        field = _parse_tool_field(parser, section_name=section_name)
        if field.name in seen:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Duplicate {section_name} field '{field.name}'.",
                    why="Each field in a tool block must be unique.",
                    fix="Rename or remove the duplicate field.",
                    example=_tool_decl_example("summarize a csv file"),
                ),
                line=field.line,
                column=field.column,
            )
        seen.add(field.name)
        fields.append(field)
        parser._match("NEWLINE")
    parser._expect("DEDENT", f"Expected end of {section_name} block")
    while parser._match("NEWLINE"):
        pass
    return fields


def _parse_tool_field(parser, *, section_name: str) -> ast.ToolField:
    name, line, column = _read_phrase_until(parser, stop_type="IS", context=f"{section_name} field")
    parser._expect("IS", f"Expected 'is' after {section_name} field name")
    required = True
    if _match_word(parser, "optional"):
        required = False
    type_tok = parser._current()
    raw_type = None
    if type_tok.type == "TEXT":
        raw_type = "text"
        parser._advance()
    elif type_tok.type.startswith("TYPE_"):
        parser._advance()
        raw_type = type_from_token(type_tok)
    else:
        raise Namel3ssError(
            build_guidance_message(
                what=f"Expected {section_name} field type.",
                why="Tool fields must declare a type.",
                fix="Use text, number, boolean, or json.",
                example=_tool_decl_example("summarize a csv file"),
            ),
            line=type_tok.line,
            column=type_tok.column,
        )
    canonical_type, type_was_alias = canonicalize_type_name(raw_type)
    if type_was_alias and not getattr(parser, "allow_legacy_type_aliases", True):
        raise Namel3ssError(
            f"N3PARSER_TYPE_ALIAS_DISALLOWED: Type alias '{raw_type}' is not allowed. Use '{canonical_type}'. "
            "Fix: run `n3 app.ai format` to rewrite aliases.",
            line=type_tok.line,
            column=type_tok.column,
        )
    if canonical_type not in _SUPPORTED_FIELD_TYPES:
        raise Namel3ssError(
            build_guidance_message(
                what=f"Unsupported {section_name} field type '{raw_type}'.",
                why="Only text, number, boolean, and json are supported.",
                fix="Update the field type to a supported value.",
                example=_tool_decl_example("summarize a csv file"),
            ),
            line=type_tok.line,
            column=type_tok.column,
        )
    return ast.ToolField(name=name, type_name=canonical_type, required=required, line=line, column=column)


def _read_phrase_until(parser, *, stop_type: str, context: str) -> tuple[str, int, int]:
    tokens = []
    while True:
        tok = parser._current()
        if tok.type == stop_type:
            break
        if tok.type in {"NEWLINE", "INDENT", "DEDENT", "COLON"}:
            raise Namel3ssError(f"Expected {context}", line=tok.line, column=tok.column)
        if tok.type in {"COMMA", "LPAREN", "RPAREN", "LBRACKET", "RBRACKET", "PLUS", "MINUS", "STAR", "POWER", "SLASH"}:
            raise Namel3ssError(f"Expected {context}", line=tok.line, column=tok.column)
        tokens.append(tok)
        parser._advance()
    if not tokens:
        tok = parser._current()
        raise Namel3ssError(f"Expected {context}", line=tok.line, column=tok.column)
    return _phrase_text(tokens), tokens[0].line, tokens[0].column


def _phrase_text(tokens) -> str:
    parts: list[str] = []
    for tok in tokens:
        if tok.type == "DOT":
            if parts:
                parts[-1] = f"{parts[-1]}."
            else:
                parts.append(".")
            continue
        value = tok.value
        if isinstance(value, bool):
            text = "true" if value else "false"
        elif value is None:
            text = ""
        else:
            text = str(value)
        if not text:
            continue
        if parts and parts[-1].endswith("."):
            parts[-1] = f"{parts[-1]}{text}"
        else:
            parts.append(text)
    return " ".join(parts).strip()


def _is_word(tok, value: str) -> bool:
    return isinstance(tok.value, str) and tok.value.strip().lower() == value


def _match_word(parser, value: str) -> bool:
    if _is_word(parser._current(), value):
        parser._advance()
        return True
    return False


def _expect_word(parser, value: str) -> None:
    if not _match_word(parser, value):
        tok = parser._current()
        raise Namel3ssError(f"Expected '{value}'", line=tok.line, column=tok.column)


def _tool_decl_example(tool_name: str) -> str:
    return (
        f'tool "{tool_name}":\n'
        "  implemented using python\n\n"
        "  input:\n"
        "    web address is text\n\n"
        "  output:\n"
        "    data is json"
    )


def _old_tool_syntax_message() -> str:
    return build_guidance_message(
        what="Old tool syntax is no longer supported.",
        why="Tools must be declared and called in English-first style.",
        fix="Rewrite tool declarations and calls using the English tool blocks.",
        example=(
            "tool \"get data from a web address\":\n"
            "  implemented using python\n\n"
            "  input:\n"
            "    web address is text\n\n"
            "  output:\n"
            "    data is json\n\n"
            "let response is get data from a web address:\n"
            "  web address is \"https://example.com\""
        ),
    )


__all__ = ["parse_tool", "_old_tool_syntax_message"]
