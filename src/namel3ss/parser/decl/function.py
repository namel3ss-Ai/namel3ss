from __future__ import annotations

from typing import List

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.lang.types import canonicalize_type_name
from namel3ss.parser.decl.record import type_from_token


_SUPPORTED_TYPES = {"text", "number", "boolean", "json", "list", "map"}


def parse_function_decl(parser) -> ast.FunctionDecl:
    define_tok = parser._advance()
    _expect_word(parser, "function")
    name_tok = parser._expect("STRING", "Expected function name string")
    parser._expect("COLON", "Expected ':' after function name")
    parser._expect("NEWLINE", "Expected newline after function header")
    parser._expect("INDENT", "Expected indented function body")

    inputs: List[ast.FunctionParam] | None = None
    outputs: List[ast.FunctionParam] | None = None
    body: List[ast.Statement] = []
    saw_body = False

    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        tok = parser._current()
        if tok.type in {"IDENT", "INPUT"} and tok.value == "input":
            if saw_body:
                raise Namel3ssError("Input block must come before function statements", line=tok.line, column=tok.column)
            if inputs is not None:
                raise Namel3ssError("Function input block is declared more than once", line=tok.line, column=tok.column)
            inputs = _parse_function_fields(parser, section_name="input", allow_optional=False)
            continue
        if tok.type == "IDENT" and tok.value == "output":
            if saw_body:
                raise Namel3ssError("Output block must come before function statements", line=tok.line, column=tok.column)
            if outputs is not None:
                raise Namel3ssError("Function output block is declared more than once", line=tok.line, column=tok.column)
            outputs = _parse_function_fields(parser, section_name="output", allow_optional=True)
            continue
        saw_body = True
        stmt = parser._parse_statement()
        if isinstance(stmt, list):
            body.extend(stmt)
        else:
            body.append(stmt)
        while parser._match("NEWLINE"):
            pass

    parser._expect("DEDENT", "Expected end of function body")
    while parser._match("NEWLINE"):
        pass

    if inputs is None:
        raise Namel3ssError("Function input block is required", line=define_tok.line, column=define_tok.column)

    signature = ast.FunctionSignature(
        inputs=inputs,
        outputs=outputs,
        line=define_tok.line,
        column=define_tok.column,
    )
    return ast.FunctionDecl(
        name=name_tok.value,
        signature=signature,
        body=body,
        line=define_tok.line,
        column=define_tok.column,
    )


def _parse_function_fields(
    parser,
    *,
    section_name: str,
    allow_optional: bool,
) -> List[ast.FunctionParam]:
    parser._advance()
    parser._expect("COLON", f"Expected ':' after {section_name}")
    parser._expect("NEWLINE", f"Expected newline after {section_name}")
    parser._expect("INDENT", f"Expected indented {section_name} block")
    fields: List[ast.FunctionParam] = []
    seen: set[str] = set()
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        name, line, column = _read_phrase_until(parser, stop_type="IS", context=f"{section_name} field")
        parser._expect("IS", f"Expected 'is' after {section_name} field name")
        required = True
        saw_optional = _match_word(parser, "optional")
        type_tok = parser._current()
        raw_type = None
        if type_tok.type == "TEXT":
            raw_type = "text"
            parser._advance()
        elif type_tok.type.startswith("TYPE_"):
            parser._advance()
            raw_type = type_from_token(type_tok)
        else:
            raise Namel3ssError(f"Expected {section_name} field type", line=type_tok.line, column=type_tok.column)
        if _match_word(parser, "optional"):
            saw_optional = True
        if saw_optional:
            if not allow_optional:
                tok = parser._current()
                raise Namel3ssError("Input fields cannot be optional", line=tok.line, column=tok.column)
            required = False
        canonical_type, type_was_alias = canonicalize_type_name(raw_type)
        if type_was_alias and not getattr(parser, "allow_legacy_type_aliases", True):
            raise Namel3ssError(
                f"N3PARSER_TYPE_ALIAS_DISALLOWED: Type alias '{raw_type}' is not allowed. Use '{canonical_type}'. "
                "Fix: run `n3 app.ai format` to rewrite aliases.",
                line=type_tok.line,
                column=type_tok.column,
            )
        if canonical_type not in _SUPPORTED_TYPES:
            raise Namel3ssError(f"Unsupported {section_name} field type '{canonical_type}'", line=type_tok.line, column=type_tok.column)
        if name in seen:
            raise Namel3ssError(f"Duplicate {section_name} field '{name}'", line=line, column=column)
        seen.add(name)
        fields.append(
            ast.FunctionParam(
                name=name,
                type_name=canonical_type,
                required=required,
                line=line,
                column=column,
            )
        )
        parser._match("NEWLINE")
    parser._expect("DEDENT", f"Expected end of {section_name} block")
    while parser._match("NEWLINE"):
        pass
    return fields


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


__all__ = ["parse_function_decl"]
