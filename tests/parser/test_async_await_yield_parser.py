from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.parser.core import parse


def test_async_await_yield_and_parallel_steps_parse() -> None:
    source = (
        'spec is "1.0"\n\n'
        'define function "make value":\n'
        '  input:\n'
        '    value is number\n'
        '  output:\n'
        '    value is number\n'
        '  return map:\n'
        '    "value" is value\n\n'
        'flow "demo":\n'
        '  let future_task is async call function "make value":\n'
        "    value is 1\n"
        "  await future_task\n"
        "  yield future_task\n"
        "  parallel:\n"
        "    let first is 1\n"
        "    let second is 2\n"
        "  return second\n"
    )
    program = parse(source)
    flow = program.flows[0]
    assert isinstance(flow.body[0], ast.Let)
    assert isinstance(flow.body[0].expression, ast.AsyncCallExpr)
    assert isinstance(flow.body[0].expression.expression, ast.CallFunctionExpr)
    assert isinstance(flow.body[1], ast.Await)
    assert isinstance(flow.body[2], ast.Yield)
    assert isinstance(flow.body[3], ast.ParallelBlock)
    assert [task.name for task in flow.body[3].tasks] == ["step_1", "step_2"]
