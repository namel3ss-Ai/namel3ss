from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.lang.keywords import is_keyword
from namel3ss.parser.decl.page_common import (
    _is_param_ref,
    _is_visibility_rule_start,
    _parse_param_ref,
    _parse_string_value,
    _parse_visibility_clause,
    _parse_visibility_rule_block,
    _parse_visibility_rule_line,
    _validate_visibility_combo,
)
from namel3ss.parser.diagnostics import reserved_identifier_diagnostic


def parse_use_item(parser, tok, *, allow_pattern_params: bool = False) -> ast.PageItem:
    parser._advance()
    kind_tok = parser._current()
    if kind_tok.type == "IDENT" and kind_tok.value == "ui_pack":
        parser._advance()
        pack_tok = parser._expect("STRING", "Expected ui_pack name string")
        frag_tok = parser._current()
        if frag_tok.type != "IDENT" or frag_tok.value != "fragment":
            raise Namel3ssError("Expected fragment name for ui_pack use", line=frag_tok.line, column=frag_tok.column)
        parser._advance()
        name_tok = parser._expect("STRING", "Expected fragment name string")
        visibility = _parse_visibility_clause(parser, allow_pattern_params=allow_pattern_params)
        visibility_rule = _parse_visibility_rule_block(parser, allow_pattern_params=allow_pattern_params)
        _validate_visibility_combo(visibility, visibility_rule, line=tok.line, column=tok.column)
        return ast.UseUIPackItem(
            pack_name=pack_tok.value,
            fragment_name=name_tok.value,
            visibility=visibility,
            visibility_rule=visibility_rule,
            line=tok.line,
            column=tok.column,
        )
    if kind_tok.type in {"IDENT", "PATTERN"} and kind_tok.value == "pattern":
        parser._advance()
        pattern_tok = parser._expect("STRING", "Expected pattern name string")
        visibility = _parse_visibility_clause(parser, allow_pattern_params=allow_pattern_params)
        arguments = None
        visibility_rule = None
        if parser._match("COLON"):
            arguments, visibility_rule = _parse_pattern_arguments(parser, allow_pattern_params=allow_pattern_params)
            _validate_visibility_combo(visibility, visibility_rule, line=tok.line, column=tok.column)
        else:
            visibility_rule = _parse_visibility_rule_block(parser, allow_pattern_params=allow_pattern_params)
            _validate_visibility_combo(visibility, visibility_rule, line=tok.line, column=tok.column)
        return ast.UsePatternItem(
            pattern_name=pattern_tok.value,
            arguments=arguments,
            visibility=visibility,
            visibility_rule=visibility_rule,
            line=tok.line,
            column=tok.column,
        )
    raise Namel3ssError("Pages only support 'use ui_pack' or 'use pattern'", line=kind_tok.line, column=kind_tok.column)


def _parse_pattern_arguments(parser, *, allow_pattern_params: bool) -> tuple[list[ast.PatternArgument], ast.VisibilityRule | None]:
    parser._expect("NEWLINE", "Expected newline after pattern invocation")
    parser._expect("INDENT", "Expected indented pattern arguments")
    arguments: list[ast.PatternArgument] = []
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
        name_tok = parser._current()
        if name_tok.type != "IDENT":
            raise Namel3ssError("Pattern arguments must start with a name", line=name_tok.line, column=name_tok.column)
        if is_keyword(name_tok.value) and not getattr(name_tok, "escaped", False):
            guidance, details = reserved_identifier_diagnostic(name_tok.value)
            raise Namel3ssError(guidance, line=name_tok.line, column=name_tok.column, details=details)
        parser._advance()
        if name_tok.value in seen:
            raise Namel3ssError(
                f"Pattern argument '{name_tok.value}' is duplicated",
                line=name_tok.line,
                column=name_tok.column,
            )
        parser._expect("IS", "Expected 'is' after argument name")
        value = _parse_pattern_argument_value(parser, allow_pattern_params=allow_pattern_params)
        arguments.append(ast.PatternArgument(name=name_tok.value, value=value, line=name_tok.line, column=name_tok.column))
        seen.add(name_tok.value)
        parser._match("NEWLINE")
    parser._expect("DEDENT", "Expected end of pattern arguments")
    if not arguments and visibility_rule is None:
        tok = parser._current()
        raise Namel3ssError("Pattern arguments block has no entries", line=tok.line, column=tok.column)
    return arguments, visibility_rule


def _parse_pattern_argument_value(parser, *, allow_pattern_params: bool) -> object:
    if allow_pattern_params and _is_param_ref(parser):
        return _parse_param_ref(parser)
    tok = parser._current()
    if tok.type == "STRING":
        parser._advance()
        return tok.value
    if tok.type == "NUMBER":
        parser._advance()
        return tok.value
    if tok.type == "BOOLEAN":
        parser._advance()
        return bool(tok.value)
    raise Namel3ssError("Pattern arguments must be literal values", line=tok.line, column=tok.column)


__all__ = ["parse_use_item"]
