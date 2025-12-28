from namel3ss.runtime.memory.events import EVENT_DECISION, EVENT_PREFERENCE
from namel3ss.runtime.memory_lanes.context import resolve_team_id
import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.memory_lanes.model import (
    LANE_AGENT,
    LANE_MY,
    LANE_SYSTEM,
    LANE_TEAM,
    agent_lane_key,
    ensure_lane_meta,
    is_agent_lane_item,
    lane_can_change,
    lane_for_space,
    lane_visibility,
    validate_lane_rules,
)
from namel3ss.runtime.memory_lanes.summary import build_team_summary
from namel3ss.runtime.memory_policy.defaults import default_contract
from namel3ss.runtime.memory_policy.evaluation import evaluate_lane_promotion
from namel3ss.runtime.memory.spaces import SPACE_PROJECT, SPACE_SESSION, SPACE_SYSTEM, SpaceContext, store_key
from namel3ss.runtime.memory_timeline.diff import PhaseDiff
from namel3ss.runtime.memory_timeline.snapshot import SnapshotItem


def test_lane_defaults_and_visibility():
    assert lane_for_space(SPACE_SESSION) == LANE_MY
    assert lane_for_space(SPACE_PROJECT) == LANE_TEAM
    assert lane_for_space(SPACE_SYSTEM) == LANE_SYSTEM
    assert lane_visibility(LANE_MY) == "me"
    assert lane_visibility(LANE_AGENT) == "me"
    assert lane_visibility(LANE_TEAM) == "team"
    assert lane_visibility(LANE_SYSTEM) == "all"
    assert lane_can_change(LANE_SYSTEM) is False
    meta = ensure_lane_meta({}, lane=LANE_TEAM)
    lane, visible_to, can_change = validate_lane_rules({"meta": meta})
    assert lane == LANE_TEAM
    assert visible_to == "team"
    assert can_change is True


def test_agent_lane_requires_agent_id():
    meta = ensure_lane_meta({}, lane=LANE_AGENT, agent_id="agent-a")
    lane, visible_to, can_change = validate_lane_rules({"meta": meta})
    assert lane == LANE_AGENT
    assert visible_to == "me"
    assert can_change is True
    assert is_agent_lane_item({"meta": meta}) is True
    with pytest.raises(Namel3ssError):
        validate_lane_rules({"meta": ensure_lane_meta({}, lane=LANE_AGENT)})


def test_agent_lane_key_is_deterministic():
    ctx = SpaceContext(session_id="session", user_id="user", project_id="proj")
    assert agent_lane_key(ctx, space=SPACE_PROJECT, agent_id="agent one") == "project:proj:agent:agent_one"


def test_store_key_includes_lane():
    assert store_key("session", "anon", "my") == "session:anon:my"


def test_team_id_deterministic_and_configurable():
    team_id = resolve_team_id(project_root="/tmp/project", app_path=None, config=None)
    again = resolve_team_id(project_root="/tmp/project", app_path=None, config=None)
    assert team_id == again
    override = resolve_team_id(project_root=None, app_path=None, config={"team_id": "team-alpha"})
    assert override == "team-alpha"


def test_lane_promotion_policy_allows_decision_denies_preference():
    contract = default_contract(write_policy="normal", forget_policy="decay")
    allowed = evaluate_lane_promotion(
        contract,
        lane=LANE_TEAM,
        space=SPACE_PROJECT,
        event_type=EVENT_DECISION,
    )
    denied = evaluate_lane_promotion(
        contract,
        lane=LANE_TEAM,
        space=SPACE_PROJECT,
        event_type=EVENT_PREFERENCE,
    )
    assert allowed.allowed is True
    assert denied.allowed is False


def test_team_summary_is_bracketless_and_stable():
    diff = PhaseDiff(
        from_phase_id="phase-1",
        to_phase_id="phase-2",
        added=[SnapshotItem("id-1", "semantic", "decision:ship weekly")],
        deleted=[SnapshotItem("id-2", "semantic", "context:note")],
        replaced=[(
            SnapshotItem("id-3", "semantic", "preference:style"),
            SnapshotItem("id-4", "semantic", "decision:style"),
            "decision:style",
        )],
    )
    summary = build_team_summary(diff)
    assert summary.title == "Team memory summary"
    assert summary.lines
    for line in summary.lines:
        assert all(ch not in line for ch in "[]{}()")
