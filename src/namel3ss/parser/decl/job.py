from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.parser.stmt.common import parse_statements


def parse_job(parser) -> ast.JobDecl:
    job_tok = parser._expect("JOB", "Expected 'job' declaration")
    name_tok = parser._expect("STRING", "Expected job name string")
    when_expr = None
    if parser._match("WHEN"):
        when_expr = parser._parse_expression()
    if not parser._match("COLON"):
        raise Namel3ssError(
            build_guidance_message(
                what="Job header is missing ':'.",
                why="Jobs must declare a block of statements.",
                fix='Add ":" after the job header.',
                example='job "refresh cache":\n  return "ok"',
            ),
            line=name_tok.line,
            column=name_tok.column,
        )
    parser._expect("NEWLINE", "Expected newline after job header")
    parser._expect("INDENT", "Expected indented job body")
    body = parse_statements(parser, until={"DEDENT"})
    parser._expect("DEDENT", "Expected end of job body")
    while parser._match("NEWLINE"):
        pass
    return ast.JobDecl(
        name=name_tok.value,
        body=body,
        when=when_expr,
        line=job_tok.line,
        column=job_tok.column,
    )


__all__ = ["parse_job"]
