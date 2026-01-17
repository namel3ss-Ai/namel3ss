from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.parser.core.helpers import parse_reference_name


def parse_enqueue_job(parser) -> ast.EnqueueJob:
    enqueue_tok = parser._advance()
    if not parser._match("JOB"):
        raise Namel3ssError("Expected 'job' after enqueue", line=enqueue_tok.line, column=enqueue_tok.column)
    name_tok = parser._current()
    job_name = parse_reference_name(parser, context="job")
    input_expr = None
    if parser._match("WITH"):
        parser._expect("INPUT", "Expected 'input' after with")
        parser._expect("COLON", "Expected ':' after input")
        input_expr = parser._parse_expression()
    return ast.EnqueueJob(
        job_name=job_name,
        input_expr=input_expr,
        line=name_tok.line,
        column=name_tok.column,
    )


__all__ = ["parse_enqueue_job"]
