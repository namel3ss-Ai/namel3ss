import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.parser.core import parse


def test_agent_team_list_form_parses() -> None:
    source = 'spec is "1.0"\n\nteam of agents\n  "planner"\n  "reviewer"\n'
    program = parse(source)
    team = program.agent_team
    assert team is not None
    assert [member.name for member in team.members] == ["planner", "reviewer"]
    assert [member.role for member in team.members] == [None, None]


def test_agent_team_block_form_parses_role() -> None:
    source = 'spec is "1.0"\n\nteam of agents\n  agent "planner"\n    role is "Plans"\n'
    program = parse(source)
    team = program.agent_team
    assert team is not None
    assert team.members[0].name == "planner"
    assert team.members[0].role == "Plans"


def test_agent_team_mixed_forms_rejected() -> None:
    source = (
        'spec is "1.0"\n\n'
        'team of agents\n'
        '  "planner"\n'
        '  agent "reviewer"\n'
        '    role is "Reviews"\n'
    )
    with pytest.raises(Namel3ssError) as err:
        parse(source)
    assert "mixes" in str(err.value)


def test_agent_team_unknown_field_rejected() -> None:
    source = (
        'spec is "1.0"\n\n'
        'team of agents\n'
        '  agent "planner"\n'
        '    title is "Plans"\n'
    )
    with pytest.raises(Namel3ssError) as err:
        parse(source)
    assert "Unknown field" in str(err.value)


def test_agent_team_role_declared_twice_rejected() -> None:
    source = (
        'spec is "1.0"\n\n'
        'team of agents\n'
        '  agent "planner"\n'
        '    role is "Plans"\n'
        '    role is "Extra"\n'
    )
    with pytest.raises(Namel3ssError) as err:
        parse(source)
    assert "more than once" in str(err.value)
