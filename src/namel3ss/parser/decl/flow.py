from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.parser.stmt.common import parse_statements


def parse_flow(parser) -> ast.Flow:
    flow_tok = parser._expect("FLOW", "Expected 'flow' declaration")
    name_tok = parser._expect("STRING", "Expected flow name string")
    parser._expect("COLON", "Expected ':' after flow name")
    requires_expr = None
    audited = False
    while True:
        if _match_ident_value(parser, "requires"):
            if requires_expr is not None:
                raise Namel3ssError(
                    build_guidance_message(
                        what="Flow declares requires more than once.",
                        why="Each flow may only have a single requires clause.",
                        fix="Keep a single requires clause on the flow header.",
                        example='flow "delete_order": requires identity.role is "admin"',
                    ),
                    line=flow_tok.line,
                    column=flow_tok.column,
                )
            requires_expr = parser._parse_expression()
            continue
        if _match_ident_value(parser, "audited"):
            if audited:
                raise Namel3ssError(
                    build_guidance_message(
                        what="Flow declares audited more than once.",
                        why="Auditing is a single flag on the flow header.",
                        fix="Remove the extra audited keyword.",
                        example='flow "update_order": audited',
                    ),
                    line=flow_tok.line,
                    column=flow_tok.column,
                )
            audited = True
            continue
        break
    parser._expect("NEWLINE", "Expected newline after flow header")
    parser._expect("INDENT", "Expected indented block for flow body")
    body = parse_statements(parser, until={"DEDENT"})
    parser._expect("DEDENT", "Expected block end")
    while parser._match("NEWLINE"):
        pass
    return ast.Flow(
        name=name_tok.value,
        body=body,
        requires=requires_expr,
        audited=audited,
        line=flow_tok.line,
        column=flow_tok.column,
    )


def _match_ident_value(parser, value: str) -> bool:
    tok = parser._current()
    if tok.type == "IDENT" and tok.value == value:
        parser._advance()
        return True
    return False


__all__ = ["parse_flow"]
