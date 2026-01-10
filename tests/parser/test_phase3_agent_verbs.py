from __future__ import annotations

from namel3ss.ast import nodes as ast
from tests.conftest import parse_program


def test_shorthand_agent_call_parses() -> None:
    source = '''
ai "mock":
  model is "mock"

agent "planner":
  ai is "mock"

flow "demo":
  planner drafts "goal" as plan
'''
    program = parse_program(source)
    stmt = program.flows[0].body[0]
    assert isinstance(stmt, ast.RunAgentStmt)
    assert stmt.agent_name == "planner"
    assert stmt.target == "plan"


def test_explicit_agent_call_parses() -> None:
    source = '''
ai "mock":
  model is "mock"

agent "planner":
  ai is "mock"

flow "demo":
  agent "planner" drafts "goal" as plan
'''
    program = parse_program(source)
    stmt = program.flows[0].body[0]
    assert isinstance(stmt, ast.RunAgentStmt)
    assert stmt.agent_name == "planner"
    assert stmt.target == "plan"


def test_in_parallel_block_parses() -> None:
    source = '''
ai "mock":
  model is "mock"

agent "critic":
  ai is "mock"

agent "researcher":
  ai is "mock"

flow "demo":
  in parallel:
    critic reviews plan as critic_text
    researcher enriches plan as researcher_text
  merge policy is "all" as feedback
'''
    program = parse_program(source)
    stmt = program.flows[0].body[0]
    assert isinstance(stmt, ast.RunAgentsParallelStmt)
    assert stmt.target == "feedback"
    assert stmt.merge is not None
    assert stmt.merge.policy == "all"
    assert [entry.agent_name for entry in stmt.entries] == ["critic", "researcher"]


def test_core_agent_calls_still_parse() -> None:
    source = '''
ai "mock":
  model is "mock"

agent "planner":
  ai is "mock"

agent "critic":
  ai is "mock"

flow "demo":
  run agent "planner" with input: "goal" as plan
  run agents in parallel:
    agent "critic" with input: plan
  merge:
    policy is "all"
  as feedback
'''
    program = parse_program(source)
    assert isinstance(program.flows[0].body[0], ast.RunAgentStmt)
    assert isinstance(program.flows[0].body[1], ast.RunAgentsParallelStmt)
