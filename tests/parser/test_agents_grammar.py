import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.parser.core import parse


def test_agent_decl_requires_ai() -> None:
    source = 'agent "planner":\n  system_prompt is "hi"\n'
    with pytest.raises(Namel3ssError):
        parse(source)


def test_run_agent_requires_as() -> None:
    source = 'run agent "planner" with input: "task"\n'
    with pytest.raises(Namel3ssError):
        parse(source)


def test_run_agents_parallel_requires_entry() -> None:
    source = 'run agents in parallel:\n  \n  \nas results\n'
    with pytest.raises(Namel3ssError):
        parse(source)


def test_run_agents_parallel_missing_as() -> None:
    source = 'run agents in parallel:\n  agent "a" with input: 1\n'
    with pytest.raises(Namel3ssError):
        parse(source)
