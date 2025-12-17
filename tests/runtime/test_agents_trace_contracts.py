from namel3ss.ir import nodes as ir
from namel3ss.runtime.ai.mock_provider import MockProvider
from namel3ss.runtime.executor import Executor


def _ai_profile(name: str = "assistant"):
    return ir.AIDecl(
        name=name,
        model="gpt-4.1",
        provider="mock",
        system_prompt="hi",
        exposed_tools=[],
        memory=ir.AIMemory(short_term=2, semantic=False, profile=False, line=1, column=1),
        line=1,
        column=1,
    )


def test_sequential_agent_trace_contains_agent_name():
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
        ai_profiles={"assistant": _ai_profile()},
        agents={"planner": ir.AgentDecl(name="planner", ai_name="assistant", system_prompt=None, line=1, column=1)},
        ai_provider=MockProvider(),
    )
    result = executor.run()
    assert len(result.traces) == 1
    trace = result.traces[0]
    assert trace.agent_name == "planner"
    assert trace.ai_name == "assistant"
    assert trace.ai_profile_name == "assistant"
    assert hasattr(trace, "tool_calls") and trace.tool_calls == []
    assert hasattr(trace, "tool_results") and trace.tool_results == []


def test_parallel_agent_wrapper_trace_and_order():
    entries = [
        ir.ParallelAgentEntry(agent_name="critic", input_expr=ir.Literal(value="A", line=2, column=5), line=2, column=3),
        ir.ParallelAgentEntry(agent_name="researcher", input_expr=ir.Literal(value="B", line=3, column=5), line=3, column=3),
    ]
    flow = ir.Flow(
        name="demo",
        body=[ir.RunAgentsParallelStmt(entries=entries, target="results", line=1, column=1)],
        line=1,
        column=1,
    )
    profiles = {"assistant": _ai_profile()}
    agents = {
        "critic": ir.AgentDecl(name="critic", ai_name="assistant", system_prompt=None, line=1, column=1),
        "researcher": ir.AgentDecl(name="researcher", ai_name="assistant", system_prompt=None, line=1, column=1),
    }
    executor = Executor(flow, ai_profiles=profiles, agents=agents, ai_provider=MockProvider())
    result = executor.run()
    outputs = executor.locals["results"]
    assert outputs[0].startswith("[gpt-4.1] hi :: A")
    assert outputs[1].startswith("[gpt-4.1] hi :: B")
    assert len(result.traces) == 1
    wrapper = result.traces[0]
    assert wrapper["type"] == "parallel_agents"
    assert wrapper["target"] == "results"
    agents_traces = wrapper["agents"]
    assert [a["agent_name"] for a in agents_traces] == ["critic", "researcher"]
    assert [a["output"] for a in agents_traces] == executor.locals["results"]


def test_parallel_agent_failure_propagates_with_name():
    bad_entry = ir.ParallelAgentEntry(agent_name="bad", input_expr=ir.Literal(value=123, line=2, column=5), line=2, column=3)
    flow = ir.Flow(
        name="demo",
        body=[ir.RunAgentsParallelStmt(entries=[bad_entry], target="results", line=1, column=1)],
        line=1,
        column=1,
    )
    agents = {"bad": ir.AgentDecl(name="bad", ai_name="assistant", system_prompt=None, line=1, column=1)}
    executor = Executor(flow, ai_profiles={"assistant": _ai_profile()}, agents=agents, ai_provider=MockProvider())
    try:
        executor.run()
    except Exception as err:
        assert "Agent 'bad' failed" in str(err)
    else:
        raise AssertionError("Expected failure did not occur")
