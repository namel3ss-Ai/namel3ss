from namel3ss.agents.ids import agent_id_from_name, team_id_from_agent_ids
from namel3ss.agents.intent import build_agent_team_intent
from tests.conftest import lower_ir_program


def test_agent_id_from_name_is_stable() -> None:
    assert agent_id_from_name("Planner") == "planner"
    assert agent_id_from_name("Planner") == agent_id_from_name("planner")


def test_team_id_from_agent_ids_is_stable() -> None:
    assert team_id_from_agent_ids(["planner", "reviewer"]) == "team_planner_reviewer"


def test_agent_team_intent_respects_team_order() -> None:
    source = (
        'spec is "1.0"\n\n'
        'ai "assistant":\n'
        '  model is "gpt-4.1"\n\n'
        'agent "planner":\n'
        '  ai is "assistant"\n\n'
        'agent "reviewer":\n'
        '  ai is "assistant"\n\n'
        'team of agents\n'
        '  "reviewer"\n'
        '  "planner"\n\n'
        'flow "demo":\n'
        '  return "ok"\n'
    )
    program = lower_ir_program(source)
    intent = build_agent_team_intent(program)
    assert intent is not None
    assert [agent["name"] for agent in intent["agents"]] == ["reviewer", "planner"]
    assert intent["team_id"] == "team_reviewer_planner"
