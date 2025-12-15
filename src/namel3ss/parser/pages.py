from __future__ import annotations

from typing import List

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError


def parse_page(parser) -> ast.PageDecl:
    page_tok = parser._advance()
    name_tok = parser._expect("STRING", "Expected page name string")
    parser._expect("COLON", "Expected ':' after page name")
    parser._expect("NEWLINE", "Expected newline after page header")
    parser._expect("INDENT", "Expected indented page body")
    items: List[ast.PageItem] = []
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        items.append(parse_page_item(parser))
    parser._expect("DEDENT", "Expected end of page body")
    return ast.PageDecl(name=name_tok.value, items=items, line=page_tok.line, column=page_tok.column)


def parse_page_item(parser) -> ast.PageItem:
    tok = parser._current()
    if tok.type == "TITLE":
        parser._advance()
        parser._expect("IS", "Expected 'is' after 'title'")
        value_tok = parser._expect("STRING", "Expected title string")
        return ast.TitleItem(value=value_tok.value, line=tok.line, column=tok.column)
    if tok.type == "TEXT":
        parser._advance()
        parser._expect("IS", "Expected 'is' after 'text'")
        value_tok = parser._expect("STRING", "Expected text string")
        return ast.TextItem(value=value_tok.value, line=tok.line, column=tok.column)
    if tok.type == "FORM":
        parser._advance()
        parser._expect("IS", "Expected 'is' after 'form'")
        value_tok = parser._expect("STRING", "Expected form record name")
        return ast.FormItem(record_name=value_tok.value, line=tok.line, column=tok.column)
    if tok.type == "TABLE":
        parser._advance()
        parser._expect("IS", "Expected 'is' after 'table'")
        value_tok = parser._expect("STRING", "Expected table record name")
        return ast.TableItem(record_name=value_tok.value, line=tok.line, column=tok.column)
    if tok.type == "BUTTON":
        parser._advance()
        label_tok = parser._expect("STRING", "Expected button label string")
        parser._expect("CALLS", "Expected 'calls' in button action")
        parser._expect("FLOW", "Expected 'flow' keyword in button action")
        flow_tok = parser._expect("STRING", "Expected flow name string")
        return ast.ButtonItem(label=label_tok.value, flow_name=flow_tok.value, line=tok.line, column=tok.column)
    raise Namel3ssError(
        f"Pages are declarative; unexpected item '{tok.type.lower()}'",
        line=tok.line,
        column=tok.column,
    )
