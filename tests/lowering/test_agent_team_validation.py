import pytest

from namel3ss.errors.base import Namel3ssError
from tests.conftest import lower_ir_program


BASE = '''spec is "1.0"

ai "assistant":
  model is "gpt-4.1"

agent "planner":
  ai is "assistant"

agent "reviewer":
  ai is "assistant"

flow "demo":
  return "ok"
'''


def test_agent_team_duplicate_names_rejected() -> None:
    source = (
        'spec is "1.0"\n\n'
        'ai "assistant":\n'
        '  model is "gpt-4.1"\n\n'
        'agent "planner":\n'
        '  ai is "assistant"\n\n'
        'agent "reviewer":\n'
        '  ai is "assistant"\n\n'
        'team of agents\n'
        '  "planner"\n'
        '  "planner"\n\n'
        'flow "demo":\n'
        '  return "ok"\n'
    )
    with pytest.raises(Namel3ssError) as err:
        lower_ir_program(source)
    assert "Duplicate agent name" in str(err.value)


def test_agent_team_unknown_agent_rejected() -> None:
    source = (
        'spec is "1.0"\n\n'
        'ai "assistant":\n'
        '  model is "gpt-4.1"\n\n'
        'agent "planner":\n'
        '  ai is "assistant"\n\n'
        'team of agents\n'
        '  "planner"\n'
        '  "ghost"\n\n'
        'flow "demo":\n'
        '  return "ok"\n'
    )
    with pytest.raises(Namel3ssError) as err:
        lower_ir_program(source)
    assert "unknown agent" in str(err.value).lower()


def test_agent_team_missing_declared_agent_rejected() -> None:
    source = BASE + 'team of agents\n  "planner"\n'
    with pytest.raises(Namel3ssError) as err:
        lower_ir_program(source)
    assert "declared but not listed" in str(err.value)


def test_agent_id_collision_rejected() -> None:
    source = (
        'spec is "1.0"\n\n'
        'ai "assistant":\n'
        '  model is "gpt-4.1"\n\n'
        'agent "Team Lead":\n'
        '  ai is "assistant"\n\n'
        'agent "Team-Lead":\n'
        '  ai is "assistant"\n\n'
        'flow "demo":\n'
        '  return "ok"\n'
    )
    with pytest.raises(Namel3ssError) as err:
        lower_ir_program(source)
    assert "Agent id" in str(err.value)
