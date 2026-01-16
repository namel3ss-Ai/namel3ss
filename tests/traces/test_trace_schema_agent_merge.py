from namel3ss.traces.builders import (
    build_agent_merge_candidate,
    build_agent_merge_rejected,
    build_agent_merge_selected,
    build_agent_merge_started,
    build_agent_merge_summary,
    build_merge_applied,
)
from namel3ss.traces.schema import TRACE_VERSION, TraceEventType


def test_agent_merge_started_trace_event():
    event = build_agent_merge_started(
        policy="ranked",
        candidate_count=2,
        title="Agent merge started",
        lines=["Merge policy is ranked.", "Candidate count is 2."],
    )
    assert event["type"] == TraceEventType.AGENT_MERGE_STARTED
    assert event["trace_version"] == TRACE_VERSION
    assert event["policy"] == "ranked"
    assert event["candidate_count"] == 2


def test_agent_merge_candidate_trace_event():
    event = build_agent_merge_candidate(
        policy="ranked",
        agent_name="alpha",
        status="valid",
        score="2",
        title="Agent merge candidate",
        lines=["Score is 2."],
    )
    assert event["type"] == TraceEventType.AGENT_MERGE_CANDIDATE
    assert event["policy"] == "ranked"
    assert event["agent_name"] == "alpha"
    assert event["status"] == "valid"
    assert event["score"] == "2"


def test_agent_merge_selected_trace_event():
    event = build_agent_merge_selected(
        policy="first_valid",
        agent_name="alpha",
        score=None,
        title="Agent merge selected",
        lines=["Selected by merge policy."],
    )
    assert event["type"] == TraceEventType.AGENT_MERGE_SELECTED
    assert event["policy"] == "first_valid"
    assert event["agent_name"] == "alpha"
    assert "score" not in event


def test_agent_merge_rejected_trace_event():
    event = build_agent_merge_rejected(
        policy="first_valid",
        agent_name="beta",
        score="1",
        title="Agent merge rejected",
        lines=["Not selected by merge policy."],
    )
    assert event["type"] == TraceEventType.AGENT_MERGE_REJECTED
    assert event["policy"] == "first_valid"
    assert event["agent_name"] == "beta"
    assert event["score"] == "1"


def test_agent_merge_summary_trace_event():
    event = build_agent_merge_summary(
        policy="consensus",
        selected_agents=["alpha"],
        rejected_agents=["beta"],
        title="Agent merge summary",
        lines=["Merge policy is consensus."],
    )
    assert event["type"] == TraceEventType.AGENT_MERGE_SUMMARY
    assert event["policy"] == "consensus"
    assert event["selected_agents"] == ["alpha"]
    assert event["rejected_agents"] == ["beta"]


def test_merge_applied_trace_event():
    event = build_merge_applied(
        policy="ranked",
        selected_agents=["alpha"],
        rejected_agents=["beta"],
        title="Merge applied",
        lines=["Merge applied."],
    )
    assert event["type"] == TraceEventType.MERGE_APPLIED
    assert event["trace_version"] == TRACE_VERSION
    assert event["policy"] == "ranked"
    assert event["selected_agents"] == ["alpha"]
    assert event["rejected_agents"] == ["beta"]
