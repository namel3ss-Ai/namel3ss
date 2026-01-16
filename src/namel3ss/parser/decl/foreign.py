from __future__ import annotations

import difflib

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.foreign.types import (
    foreign_type_suggestions,
    is_foreign_type,
    normalize_foreign_type,
)
from namel3ss.parser.decl.record import type_from_token


_FOREIGN_LANGS = {"python": "python", "js": "node"}


def parse_foreign_decl(parser) -> ast.ToolDecl:
    foreign_tok = parser._current()
    _expect_word(parser, "foreign")
    lang_tok = parser._current()
    if not isinstance(lang_tok.value, str):
        raise Namel3ssError("Expected foreign language after 'foreign'", line=lang_tok.line, column=lang_tok.column)
    language = lang_tok.value.strip().lower()
    if language not in _FOREIGN_LANGS:
        suggestion = difflib.get_close_matches(language, sorted(_FOREIGN_LANGS.keys()), n=1, cutoff=0.6)
        hint = f" Did you mean '{suggestion[0]}'?" if suggestion else ""
        raise Namel3ssError(
            build_guidance_message(
                what=f"Unknown foreign language '{language}'.{hint}",
                why="Foreign functions only support python and js.",
                fix="Use 'python' or 'js' in the foreign declaration header.",
                example=_foreign_decl_example("calculate_tax"),
            ),
            line=lang_tok.line,
            column=lang_tok.column,
        )
    parser._advance()
    _expect_word(parser, "function")
    name_tok = parser._expect("STRING", "Expected foreign function name string")
    parser._expect("NEWLINE", "Expected newline after foreign function header")
    parser._expect("INDENT", "Expected indented foreign function body")

    input_fields: list[ast.ToolField] | None = None
    output_type: str | None = None

    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        tok = parser._current()
        if _is_word(tok, "input") or tok.type == "INPUT":
            if input_fields is not None:
                raise Namel3ssError(
                    "Foreign function input is declared more than once",
                    line=tok.line,
                    column=tok.column,
                )
            input_fields = _parse_input_block(parser)
            continue
        if _is_word(tok, "output"):
            if output_type is not None:
                raise Namel3ssError(
                    "Foreign function output is declared more than once",
                    line=tok.line,
                    column=tok.column,
                )
            output_type = _parse_output_line(parser, function_name=str(name_tok.value))
            continue
        raise Namel3ssError("Unknown field in foreign function declaration", line=tok.line, column=tok.column)

    parser._expect("DEDENT", "Expected end of foreign function body")

    if input_fields is None:
        raise Namel3ssError(
            build_guidance_message(
                what=f'Foreign function "{name_tok.value}" is missing an input block.',
                why="Foreign functions must declare their inputs.",
                fix="Add an input block with parameter names and types.",
                example=_foreign_decl_example(name_tok.value),
            ),
            line=foreign_tok.line,
            column=foreign_tok.column,
        )
    if output_type is None:
        raise Namel3ssError(
            build_guidance_message(
                what=f'Foreign function "{name_tok.value}" is missing an output type.',
                why="Foreign functions must declare their output type.",
                fix="Add an output line like `output is text`.",
                example=_foreign_decl_example(name_tok.value),
            ),
            line=foreign_tok.line,
            column=foreign_tok.column,
        )

    output_fields = [
        ast.ToolField(
            name="result",
            type_name=output_type,
            required=True,
            line=foreign_tok.line,
            column=foreign_tok.column,
        )
    ]
    return ast.ToolDecl(
        name=name_tok.value,
        kind=_FOREIGN_LANGS[language],
        input_fields=input_fields,
        output_fields=output_fields,
        purity="impure",
        timeout_seconds=None,
        declared_as="foreign",
        line=foreign_tok.line,
        column=foreign_tok.column,
    )


def _parse_input_block(parser) -> list[ast.ToolField]:
    parser._advance()
    parser._expect("NEWLINE", "Expected newline after input")
    if not parser._match("INDENT"):
        return []
    fields: list[ast.ToolField] = []
    seen: set[str] = set()
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        name, line, column = _read_phrase_until(parser, stop_type="IS", context="input field")
        parser._expect("IS", "Expected 'is' after input field name")
        if _match_word(parser, "optional"):
            raise Namel3ssError("Foreign input fields cannot be optional", line=line, column=column)
        raw_type, type_tok = _parse_foreign_type(parser)
        canonical, was_alias = normalize_foreign_type(raw_type)
        if was_alias and not getattr(parser, "allow_legacy_type_aliases", True):
            raise Namel3ssError(
                f"N3PARSER_TYPE_ALIAS_DISALLOWED: Type alias '{raw_type}' is not allowed. Use '{canonical}'. "
                "Fix: run `n3 app.ai format` to rewrite aliases.",
                line=type_tok.line,
                column=type_tok.column,
            )
        if not is_foreign_type(canonical):
            suggestions = foreign_type_suggestions(raw_type)
            hint = f" Did you mean '{suggestions[0]}'?" if suggestions else ""
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Unsupported foreign input type '{raw_type}'.{hint}",
                    why="Foreign inputs must be text, number, boolean, or a list of those types.",
                    fix="Update the type to a supported value.",
                    example=_foreign_decl_example("calculate_tax"),
                ),
                line=type_tok.line,
                column=type_tok.column,
            )
        if name in seen:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Duplicate input field '{name}'.",
                    why="Foreign input parameters must be unique.",
                    fix="Rename or remove the duplicate parameter.",
                    example=_foreign_decl_example("calculate_tax"),
                ),
                line=line,
                column=column,
            )
        seen.add(name)
        fields.append(
            ast.ToolField(
                name=name,
                type_name=canonical,
                required=True,
                line=line,
                column=column,
            )
        )
        parser._match("NEWLINE")
    parser._expect("DEDENT", "Expected end of input block")
    while parser._match("NEWLINE"):
        pass
    return fields


def _parse_output_line(parser, *, function_name: str) -> str:
    parser._advance()
    parser._expect("IS", "Expected 'is' after output")
    raw_type, type_tok = _parse_foreign_type(parser)
    canonical, was_alias = normalize_foreign_type(raw_type)
    if was_alias and not getattr(parser, "allow_legacy_type_aliases", True):
        raise Namel3ssError(
            f"N3PARSER_TYPE_ALIAS_DISALLOWED: Type alias '{raw_type}' is not allowed. Use '{canonical}'. "
            "Fix: run `n3 app.ai format` to rewrite aliases.",
            line=type_tok.line,
            column=type_tok.column,
        )
    if not is_foreign_type(canonical):
        suggestions = foreign_type_suggestions(raw_type)
        hint = f" Did you mean '{suggestions[0]}'?" if suggestions else ""
        raise Namel3ssError(
            build_guidance_message(
                what=f"Unsupported foreign output type '{raw_type}'.{hint}",
                why="Foreign outputs must be text, number, boolean, or a list of those types.",
                fix="Update the type to a supported value.",
                example=_foreign_decl_example(function_name),
            ),
            line=type_tok.line,
            column=type_tok.column,
        )
    parser._match("NEWLINE")
    return canonical


def _parse_foreign_type(parser) -> tuple[str, object]:
    tok = parser._current()
    if tok.type == "IDENT" and tok.value == "list":
        parser._advance()
        _expect_word(parser, "of")
        item_tok = parser._current()
        raw = _parse_base_type(parser)
        return f"list of {raw}", item_tok
    raw = _parse_base_type(parser)
    return raw, tok


def _parse_base_type(parser) -> str:
    tok = parser._current()
    if tok.type == "TEXT":
        parser._advance()
        return "text"
    if tok.type.startswith("TYPE_"):
        parser._advance()
        return type_from_token(tok)
    if tok.type == "IDENT":
        parser._advance()
        return str(tok.value)
    raise Namel3ssError("Expected foreign type", line=tok.line, column=tok.column)


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
    return tok.type == "IDENT" and tok.value == value


def _match_word(parser, value: str) -> bool:
    tok = parser._current()
    if tok.type != "IDENT" or tok.value != value:
        return False
    parser._advance()
    return True


def _expect_word(parser, value: str) -> None:
    tok = parser._current()
    if tok.type != "IDENT" or tok.value != value:
        raise Namel3ssError(f"Expected '{value}'", line=tok.line, column=tok.column)
    parser._advance()


def _foreign_decl_example(name: str) -> str:
    return (
        f'foreign python function "{name}"\n'
        "  input\n"
        "    amount is number\n"
        "    country is text\n"
        "  output is number"
    )


__all__ = ["parse_foreign_decl"]
