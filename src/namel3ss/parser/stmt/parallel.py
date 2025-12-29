from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError


def parse_parallel(parser) -> ast.ParallelBlock:
    parallel_tok = parser._advance()
    parser._expect("COLON", "Expected ':' after parallel")
    parser._expect("NEWLINE", "Expected newline after parallel")
    parser._expect("INDENT", "Expected indented parallel block")
    tasks: list[ast.ParallelTask] = []
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        run_tok = parser._expect("RUN", "Expected 'run' in parallel block")
        name_tok = parser._expect("STRING", "Expected task name string after run")
        parser._expect("COLON", "Expected ':' after task name")
        body = parser._parse_block()
        tasks.append(
            ast.ParallelTask(
                name=name_tok.value,
                body=body,
                line=run_tok.line,
                column=run_tok.column,
            )
        )
    parser._expect("DEDENT", "Expected end of parallel block")
    if not tasks:
        raise Namel3ssError("Parallel block requires at least one task", line=parallel_tok.line, column=parallel_tok.column)
    return ast.ParallelBlock(tasks=tasks, line=parallel_tok.line, column=parallel_tok.column)


__all__ = ["parse_parallel"]
