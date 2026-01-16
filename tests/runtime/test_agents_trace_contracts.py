from namel3ss.determinism import normalize_traces
from namel3ss.ir import nodes as ir
from namel3ss.runtime.ai.mock_provider import MockProvider
from namel3ss.runtime.executor import Executor
from namel3ss.traces.schema import TraceEventType


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
    traces = normalize_traces(result.traces)
    ai_traces = [trace for trace in traces if trace.get("type") == "ai_call"]
    assert len(ai_traces) == 1
    trace = ai_traces[0]
    assert trace["agent_name"] == "planner"
    assert trace["agent_id"] == "planner"
    assert trace["ai_name"] == "assistant"
    assert trace["ai_profile_name"] == "assistant"
    assert trace["tool_calls"] == []
    assert trace["tool_results"] == []
    start = next(item for item in traces if item.get("type") == TraceEventType.AGENT_STEP_START)
    end = next(item for item in traces if item.get("type") == TraceEventType.AGENT_STEP_END)
    assert start["agent_name"] == "planner"
    assert start["agent_id"] == "planner"
    assert start["lines"][0].startswith("invoked by")
    assert end["status"] == "ok"
    assert isinstance(end.get("memory_facts"), dict)
    assert end["memory_facts"].get("last_updated_step")


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
    assert outputs[0]["text"].startswith("[gpt-4.1] hi :: A")
    assert outputs[1]["text"].startswith("[gpt-4.1] hi :: B")
    traces = normalize_traces(result.traces)
    wrapper = next(item for item in traces if item.get("type") == "parallel_agents")
    assert wrapper["type"] == "parallel_agents"
    assert wrapper["target"] == "results"
    agents_traces = wrapper["agents"]
    assert [a["agent_name"] for a in agents_traces] == ["critic", "researcher"]
    assert [a["agent_id"] for a in agents_traces] == ["critic", "researcher"]
    assert [a["output"] for a in agents_traces] == [item["text"] for item in executor.locals["results"]]


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
