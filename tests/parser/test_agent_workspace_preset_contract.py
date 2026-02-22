from __future__ import annotations

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.parser.preset_expansion import expand_language_presets
from tests.conftest import lower_ir_program


SOURCE = '''spec is "1.0"
use preset "agent_workspace":
  title is "Agent Workspace"
  model is "gpt-4o-mini"
  pattern is "single_agent"
'''


def test_agent_workspace_preset_generates_canonical_agent_contracts() -> None:
    program = lower_ir_program(SOURCE)
    ai_decl = program.ais.get("__agent_workspace_ai")
    assert ai_decl is not None
    assert ai_decl.provider == "openai"
    assert ai_decl.model == "gpt-4o-mini"
    assert ai_decl.memory.short_term == 0
    assert ai_decl.memory.semantic is False
    assert ai_decl.memory.profile is False

    assert "assistant" in program.agents
    expected_contracts = (
        "agent.route",
        "agent.retrieve",
        "agent.tool_policy",
        "agent.fallback",
        "agent.citations.format",
        "agent.answer",
    )
    for name in expected_contracts:
        assert name in program.flow_contracts

    answer_contract = program.flow_contracts.get("agent.answer")
    assert answer_contract is not None
    input_names = [field.name for field in answer_contract.signature.inputs]
    assert input_names == ["message", "context"]
    output_names = [field.name for field in answer_contract.signature.outputs]
    assert output_names == ["answer_text", "citations"]


def test_agent_workspace_preset_expansion_is_deterministic() -> None:
    first = expand_language_presets(SOURCE)
    second = expand_language_presets(SOURCE)
    assert first == second
    assert 'ai "__agent_workspace_ai":' in first
    assert 'contract flow "agent.route":' in first
    assert 'contract flow "agent.answer":' in first
    assert 'flow "agent.answer": requires true' in first
    assert 'use preset "agent_workspace"' not in first


def test_agent_workspace_preset_rejects_unknown_pattern() -> None:
    source = '''spec is "1.0"
use preset "agent_workspace":
  pattern is "unknown_pattern"
'''
    with pytest.raises(Namel3ssError) as exc:
        expand_language_presets(source)
    assert "Unknown agent_workspace pattern" in str(exc.value)


def test_agent_workspace_preset_supports_controlled_overrides() -> None:
    source = '''spec is "1.0"
use preset "agent_workspace":
  title is "Agent Workspace"

override flow "agent.route":
  return map:
    "route" is "single_agent"
    "query" is input.message
    "context" is input.context

override flow "agent.answer":
  return map:
    "answer_text" is input.message
    "citations" is list:
'''
    expanded = expand_language_presets(source)
    assert 'flow "agent.route": requires true' in expanded
    assert '"route" is "single_agent"' in expanded
    assert 'flow "agent.answer": requires true' in expanded
    assert '"answer_text" is input.message' in expanded
    assert 'use preset "agent_workspace"' not in expanded

    program = lower_ir_program(source)
    answer_contract = program.flow_contracts.get("agent.answer")
    assert answer_contract is not None
    assert [field.name for field in answer_contract.signature.inputs] == ["message", "context"]
    assert [field.name for field in answer_contract.signature.outputs] == ["answer_text", "citations"]


def test_agent_workspace_preset_rejects_unknown_override_target() -> None:
    source = '''spec is "1.0"
use preset "agent_workspace":
  title is "Agent Workspace"

override flow "agent.unknown":
  return map:
    "ok" is true
'''
    with pytest.raises(Namel3ssError) as exc:
        expand_language_presets(source)
    assert "Unsupported override target" in str(exc.value)
