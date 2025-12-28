from namel3ss.ir import nodes as ir
from namel3ss.runtime.ai.mock_provider import MockProvider
from namel3ss.runtime.executor import Executor


def _ai_profile():
    return ir.AIDecl(
        name="assistant",
        model="gpt-4.1",
        provider="mock",
        system_prompt="hi",
        exposed_tools=[],
        memory=ir.AIMemory(short_term=2, semantic=False, profile=False, line=1, column=1),
        line=1,
        column=1,
    )


def test_agent_call_records_short_term_memory_with_user_id():
    flow = ir.Flow(
        name="demo",
        body=[
            ir.RunAgentStmt(
                agent_name="planner",
                input_expr=ir.Literal(value="Task", line=2, column=5),
                target="plan",
                line=2,
                column=3,
            )
        ],
        line=1,
        column=1,
    )
    executor = Executor(
        flow,
        initial_state={"user": {"id": 1}},
        ai_profiles={"assistant": _ai_profile()},
        agents={"planner": ir.AgentDecl(name="planner", ai_name="assistant", system_prompt=None, line=1, column=1)},
        ai_provider=MockProvider(),
    )
    executor.run()
    messages = executor.memory_manager.short_term.recall("session:1:my", 10)
    sources = [m.source for m in messages]
    assert "user" in sources
    assert "ai" in sources
