from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message


def parse_use_decl(parser) -> ast.UseDecl:
    use_tok = parser._advance()
    module_tok = parser._current()
    if module_tok.type != "STRING":
        raise Namel3ssError(
            build_guidance_message(
                what="Use statement is missing a module name.",
                why="Modules are referenced by name strings under the modules/ folder.",
                fix='Use `use "inventory" as inv` with a module name string.',
                example='use "inventory" as inv',
            ),
            line=module_tok.line,
            column=module_tok.column,
        )
    parser._advance()
    if not parser._match("AS"):
        tok = parser._current()
        raise Namel3ssError(
            build_guidance_message(
                what="Use statement is missing `as`.",
                why="`as` introduces the required namespace alias.",
                fix='Use `use "<module>" as <alias>`.',
                example='use "inventory" as inv',
            ),
            line=tok.line,
            column=tok.column,
        )
    alias_tok = parser._current()
    if alias_tok.type != "IDENT":
        raise Namel3ssError(
            build_guidance_message(
                what="Use statement is missing an alias.",
                why="Aliases keep cross-module references explicit and deterministic.",
                fix="Provide a short alias after `as`.",
                example='use "inventory" as inv',
            ),
            line=alias_tok.line,
            column=alias_tok.column,
        )
    parser._advance()
    return ast.UseDecl(module=module_tok.value, alias=alias_tok.value, line=use_tok.line, column=use_tok.column)


__all__ = ["parse_use_decl"]
