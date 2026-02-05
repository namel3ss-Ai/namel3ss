from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.parser.decl.flow_steps import parse_flow_steps
from namel3ss.parser.decl.flow_ai import parse_flow_ai_block
from namel3ss.purity import EFFECTFUL_VALUE, normalize_purity


def parse_flow(parser) -> ast.Flow:
    flow_tok = parser._expect("FLOW", "Expected 'flow' declaration")
    name_tok = parser._expect("STRING", "Expected flow name string")
    requires_expr = None
    audited = False
    purity = EFFECTFUL_VALUE
    purity_set = False
    requires_expr, audited, purity, purity_set = _parse_flow_header_flags(parser, requires_expr, audited, purity, purity_set, flow_tok)
    if parser._match("COLON"):
        requires_expr, audited, purity, purity_set = _parse_flow_header_flags(
            parser,
            requires_expr,
            audited,
            purity,
            purity_set,
            flow_tok,
        )
        if not parser._match("NEWLINE"):
            if parser._current().type not in {"DEDENT", "EOF"}:
                parser._expect("NEWLINE", "Expected newline after flow header")
        if not parser._match("INDENT"):
            while parser._match("NEWLINE"):
                pass
            return ast.Flow(
                name=name_tok.value,
                body=[],
                requires=requires_expr,
                audited=audited,
                purity=purity,
                declarative=False,
                steps=None,
                line=flow_tok.line,
                column=flow_tok.column,
            )
        body, ai_metadata = _parse_flow_body(parser)
        parser._expect("DEDENT", "Expected block end")
        while parser._match("NEWLINE"):
            pass
        return ast.Flow(
            name=name_tok.value,
            body=body,
            requires=requires_expr,
            audited=audited,
            purity=purity,
            declarative=False,
            steps=None,
            ai_metadata=ai_metadata,
            line=flow_tok.line,
            column=flow_tok.column,
        )
    parser._expect("NEWLINE", "Expected newline after flow header")
    parser._expect("INDENT", "Expected indented block for flow steps")
    steps, ai_metadata = parse_flow_steps(parser)
    parser._expect("DEDENT", "Expected end of flow steps")
    while parser._match("NEWLINE"):
        pass
    return ast.Flow(
        name=name_tok.value,
        body=[],
        requires=requires_expr,
        audited=audited,
        purity=purity,
        declarative=True,
        steps=steps,
        ai_metadata=ai_metadata,
        line=flow_tok.line,
        column=flow_tok.column,
    )


def _match_ident_value(parser, value: str) -> bool:
    tok = parser._current()
    if tok.type == "IDENT" and tok.value == value:
        parser._advance()
        return True
    return False


def _parse_flow_header_flags(parser, requires_expr, audited, purity, purity_set, flow_tok):
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
        if parser._current().type == "PURITY" or _match_ident_value(parser, "purity"):
            if purity_set:
                raise Namel3ssError(
                    build_guidance_message(
                        what="Flow declares purity more than once.",
                        why="Each flow may only declare purity once.",
                        fix="Keep a single purity declaration on the flow header.",
                        example='flow "sum": purity is "pure"',
                    ),
                    line=flow_tok.line,
                    column=flow_tok.column,
                )
            if parser._current().type == "PURITY":
                parser._advance()
            parser._expect("IS", "Expected 'is' after purity")
            value_tok = parser._current()
            if not isinstance(value_tok.value, str):
                raise Namel3ssError("Expected purity string", line=value_tok.line, column=value_tok.column)
            parser._advance()
            try:
                purity = normalize_purity(value_tok.value)
            except ValueError as exc:
                raise Namel3ssError(str(exc), line=value_tok.line, column=value_tok.column) from exc
            purity_set = True
            continue
        break
    return requires_expr, audited, purity, purity_set


def _parse_flow_body(parser) -> tuple[list[ast.Statement], ast.AIFlowMetadata | None]:
    body: list[ast.Statement] = []
    ai_metadata: ast.AIFlowMetadata | None = None
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        tok = parser._current()
        if tok.type == "AI":
            if ai_metadata is not None:
                raise Namel3ssError(
                    build_guidance_message(
                        what="Flow declares ai more than once.",
                        why="Each flow may only declare a single ai block.",
                        fix="Keep a single ai block in the flow.",
                        example='flow \"summarise\":\\n  ai:\\n    model is \"gpt-4\"\\n    prompt is \"Summarise the input.\"',
                    ),
                    line=tok.line,
                    column=tok.column,
                )
            ai_metadata = parse_flow_ai_block(parser)
            continue
        stmt = parser._parse_statement()
        if isinstance(stmt, list):
            body.extend(stmt)
        else:
            body.append(stmt)
    return body, ai_metadata


__all__ = ["parse_flow"]
