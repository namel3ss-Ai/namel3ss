from namel3ss.ast import nodes as ast
from namel3ss.parser.core import parse


def test_parallel_block_parses_tasks_in_order() -> None:
    source = (
        'spec is "1.0"\n\n'
        'flow "demo":\n'
        '  parallel:\n'
        '    run "beta":\n'
        '      let beta is 2\n'
        '    run "alpha":\n'
        '      let alpha is 1\n'
    )
    program = parse(source)
    flow = program.flows[0]
    stmt = flow.body[0]
    assert isinstance(stmt, ast.ParallelBlock)
    assert [task.name for task in stmt.tasks] == ["beta", "alpha"]
    assert isinstance(stmt.tasks[0].body[0], ast.Let)
