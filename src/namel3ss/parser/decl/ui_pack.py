from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.lang.keywords import is_keyword
from namel3ss.parser.decl.page import parse_page_item


def parse_ui_pack_decl(parser) -> ast.UIPackDecl:
    pack_tok = parser._advance()
    name_tok = parser._expect("STRING", "Expected ui_pack name string")
    if isinstance(name_tok.value, str) and is_keyword(name_tok.value):
        raise Namel3ssError(
            f"'{name_tok.value}' is a reserved keyword.",
            line=name_tok.line,
            column=name_tok.column,
        )
    parser._expect("COLON", "Expected ':' after ui_pack name")
    parser._expect("NEWLINE", "Expected newline after ui_pack header")
    parser._expect("INDENT", "Expected indented ui_pack body")
    version: str | None = None
    fragments: list[ast.UIPackFragment] = []
    seen_fragments: set[str] = set()
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        tok = parser._current()
        if tok.type == "IDENT" and tok.value == "version":
            if version is not None:
                raise Namel3ssError("ui_pack version is declared more than once", line=tok.line, column=tok.column)
            parser._advance()
            parser._expect("IS", "Expected 'is' after version")
            value_tok = parser._expect("STRING", "Expected version string")
            version = value_tok.value
            if parser._match("NEWLINE"):
                continue
            continue
        if tok.type == "IDENT" and tok.value == "fragment":
            fragment = _parse_ui_pack_fragment(parser)
            if fragment.name in seen_fragments:
                raise Namel3ssError(
                    f"ui_pack fragment '{fragment.name}' is duplicated",
                    line=tok.line,
                    column=tok.column,
                )
            seen_fragments.add(fragment.name)
            fragments.append(fragment)
            continue
        raise Namel3ssError(f"Unknown ui_pack entry '{tok.value}'", line=tok.line, column=tok.column)
    parser._expect("DEDENT", "Expected end of ui_pack body")
    if version is None:
        raise Namel3ssError("ui_pack requires a version", line=pack_tok.line, column=pack_tok.column)
    if not fragments:
        raise Namel3ssError("ui_pack has no fragments", line=pack_tok.line, column=pack_tok.column)
    return ast.UIPackDecl(
        name=name_tok.value,
        version=version,
        fragments=fragments,
        line=pack_tok.line,
        column=pack_tok.column,
    )


def _parse_ui_pack_fragment(parser) -> ast.UIPackFragment:
    frag_tok = parser._advance()
    name_tok = parser._expect("STRING", "Expected fragment name string")
    if isinstance(name_tok.value, str) and is_keyword(name_tok.value):
        raise Namel3ssError(
            f"'{name_tok.value}' is a reserved keyword.",
            line=name_tok.line,
            column=name_tok.column,
        )
    parser._expect("COLON", "Expected ':' after fragment name")
    parser._expect("NEWLINE", "Expected newline after fragment header")
    parser._expect("INDENT", "Expected indented fragment body")
    items: list[ast.PageItem] = []
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        items.append(parse_page_item(parser, allow_tabs=True, allow_overlays=True))
    parser._expect("DEDENT", "Expected end of fragment body")
    if not items:
        raise Namel3ssError("Fragment block has no entries", line=frag_tok.line, column=frag_tok.column)
    return ast.UIPackFragment(
        name=name_tok.value,
        items=items,
        line=frag_tok.line,
        column=frag_tok.column,
    )


__all__ = ["parse_ui_pack_decl"]
