import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir
from namel3ss.runtime.executor.parallel.isolation import validate_parallel_task


class DummyContext:
    def __init__(self, tools=None, ai_profiles=None, agents=None) -> None:
        self.tools = tools or {}
        self.ai_profiles = ai_profiles or {}
        self.agents = agents or {}


def _task_with_tool(tool_name: str) -> ir.ParallelTask:
    expr = ir.ToolCallExpr(tool_name=tool_name, arguments=[], line=1, column=1)
    stmt = ir.Let(name="value", expression=expr, constant=False, line=1, column=1)
    return ir.ParallelTask(name="alpha", body=[stmt], line=1, column=1)


def test_parallel_allows_pure_tools() -> None:
    tool = ir.ToolDecl(
        name="safe tool",
        kind="python",
        input_fields=[],
        output_fields=[],
        purity="pure",
        line=1,
        column=1,
    )
    ctx = DummyContext(tools={"safe tool": tool})
    task = _task_with_tool("safe tool")
    validate_parallel_task(ctx, task)


def test_parallel_blocks_impure_tools() -> None:
    tool = ir.ToolDecl(
        name="risky tool",
        kind="python",
        input_fields=[],
        output_fields=[],
        purity="impure",
        line=1,
        column=1,
    )
    ctx = DummyContext(tools={"risky tool": tool})
    task = _task_with_tool("risky tool")
    with pytest.raises(Namel3ssError, match="Parallel tasks only allow pure tools"):
        validate_parallel_task(ctx, task)
