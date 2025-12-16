from __future__ import annotations

from namel3ss.ast import nodes as ast


def parse_save(parser) -> ast.Save:
    tok = parser._advance()
    name_tok = parser._expect("IDENT", "Expected record name after 'save'")
    return ast.Save(record_name=name_tok.value, line=tok.line, column=tok.column)


def parse_find(parser) -> ast.Find:
    tok = parser._advance()
    name_tok = parser._expect("IDENT", "Expected record name after 'find'")
    parser._expect("WHERE", "Expected 'where' in find statement")
    predicate = parser._parse_expression()
    return ast.Find(record_name=name_tok.value, predicate=predicate, line=tok.line, column=tok.column)
