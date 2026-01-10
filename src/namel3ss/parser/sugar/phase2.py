from __future__ import annotations

from dataclasses import dataclass
from typing import List

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.parser.expr.calls import looks_like_tool_call, parse_tool_call_expr
from namel3ss.parser.expr.common import read_attr_name
from namel3ss.parser.sugar.diagnostics import expected_block_error, expected_value_error


@dataclass
class ClearStmt(ast.Statement):
    record_names: List[str]


@dataclass
class SaveField(ast.Node):
    path: List[str]
    expression: ast.Expression


@dataclass
class SaveRecordStmt(ast.Statement):
    record_name: str
    fields: List[SaveField]


@dataclass
class NoticeStmt(ast.Statement):
    message: str


def parse_clear(parser) -> ClearStmt:
    clear_tok = parser._advance()
    if parser._match("COLON"):
        parser._expect("NEWLINE", "Expected newline after clear:")
        if not parser._match("INDENT"):
            tok = parser._current()
            raise expected_block_error(
                tok,
                label="Clear",
                example='clear:\n  "PlannerOutput"\n  "RunSummary"',
            )
        record_names: List[str] = []
        while parser._current().type != "DEDENT":
            if parser._match("NEWLINE"):
                continue
            record_tok = parser._expect("STRING", "Expected record name string")
            record_names.append(record_tok.value)
            parser._match("NEWLINE")
        parser._expect("DEDENT", "Expected end of clear block")
        while parser._match("NEWLINE"):
            pass
        if not record_names:
            tok = parser._current()
            raise expected_value_error(
                tok,
                label="Clear records",
                example='clear:\n  "PlannerOutput"',
            )
        return ClearStmt(record_names=record_names, line=clear_tok.line, column=clear_tok.column)
    record_tok = parser._expect("STRING", "Expected record name after 'clear'")
    return ClearStmt(record_names=[record_tok.value], line=clear_tok.line, column=clear_tok.column)


def parse_save_with(parser) -> SaveRecordStmt:
    save_tok = parser._advance()
    record_tok = parser._expect("STRING", "Expected record name after 'save'")
    parser._expect("WITH", "Expected 'with' after record name")
    parser._expect("COLON", "Expected ':' after with")
    parser._expect("NEWLINE", "Expected newline after save with header")
    if not parser._match("INDENT"):
        tok = parser._current()
        raise expected_block_error(
            tok,
            label="Save",
            example='save "PlannerOutput" with:\n  text is plan.text',
        )
    fields: List[SaveField] = []
    seen: set[str] = set()
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        field_tok = parser._current()
        field_parts = _parse_save_with_field(parser)
        field_key = ".".join(field_parts)
        if field_key in seen:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Duplicate field '{field_key}' in save block.",
                    why="Each field in a save block must be unique.",
                    fix="Remove the duplicate field assignment.",
                    example='save "PlannerOutput" with:\n  text is "Plan"',
                ),
                line=field_tok.line,
                column=field_tok.column,
            )
        seen.add(field_key)
        parser._expect("IS", "Expected 'is' after field name")
        expr = _parse_save_expression(parser)
        fields.append(
            SaveField(
                path=field_parts,
                expression=expr,
                line=field_tok.line,
                column=field_tok.column,
            )
        )
        parser._match("NEWLINE")
    parser._expect("DEDENT", "Expected end of save block")
    while parser._match("NEWLINE"):
        pass
    if not fields:
        tok = parser._current()
        raise expected_value_error(
            tok,
            label="Save fields",
            example='save "PlannerOutput" with:\n  text is plan.text',
        )
    return SaveRecordStmt(record_name=record_tok.value, fields=fields, line=save_tok.line, column=save_tok.column)


def parse_notice(parser) -> NoticeStmt:
    notice_tok = parser._advance()
    message_tok = parser._expect("STRING", "Expected message after 'notice'")
    return NoticeStmt(message=message_tok.value, line=notice_tok.line, column=notice_tok.column)


def _parse_save_expression(parser) -> ast.Expression:
    if looks_like_tool_call(parser):
        return parse_tool_call_expr(parser)
    return parser._parse_expression()


def _parse_save_with_field(parser) -> list[str]:
    parts = [read_attr_name(parser, context="field name")]
    while parser._match("DOT"):
        parts.append(read_attr_name(parser, context="field name"))
    return parts


__all__ = [
    "ClearStmt",
    "NoticeStmt",
    "SaveField",
    "SaveRecordStmt",
    "parse_clear",
    "parse_notice",
    "parse_save_with",
]
