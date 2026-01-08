import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.parser.core import parse


def test_agent_decl_requires_ai() -> None:
    source = 'spec is "1.0"\n\nagent "planner":\n  system_prompt is "hi"\n'
    with pytest.raises(Namel3ssError):
        parse(source)


def test_run_agent_requires_as() -> None:
    source = 'spec is "1.0"\n\nrun agent "planner" with input: "task"\n'
    with pytest.raises(Namel3ssError):
        parse(source)


def test_run_agents_parallel_requires_entry() -> None:
    source = 'spec is "1.0"\n\nrun agents in parallel:\n  \n  \nas results\n'
    with pytest.raises(Namel3ssError):
        parse(source)


def test_run_agents_parallel_missing_as() -> None:
    source = 'spec is "1.0"\n\nrun agents in parallel:\n  agent "a" with input: 1\n'
    with pytest.raises(Namel3ssError):
        parse(source)


def test_run_agents_parallel_parses_merge_block() -> None:
    source = (
        'spec is "1.0"\n\n'
        'flow "demo":\n'
        '  run agents in parallel:\n'
        '    agent "a" with input: "x"\n'
        '    agent "b" with input: "x"\n'
        '  merge:\n'
        '    policy is "ranked"\n'
        '    score_rule is "text_length"\n'
        '  as result\n'
    )
    program = parse(source)
    stmt = program.flows[0].body[0]
    assert stmt.merge is not None
    assert stmt.merge.policy == "ranked"
    assert stmt.merge.score_rule == "text_length"


def test_run_agents_parallel_merge_requires_score_rule_or_key() -> None:
    source = (
        'spec is "1.0"\n\n'
        'flow "demo":\n'
        '  run agents in parallel:\n'
        '    agent "a" with input: "x"\n'
        '  merge:\n'
        '    policy is "ranked"\n'
        '  as result\n'
    )
    with pytest.raises(Namel3ssError):
        parse(source)
