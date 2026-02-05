from __future__ import annotations

import pytest

from namel3ss.errors.base import Namel3ssError
from tests.conftest import parse_program


def test_parse_ai_block_imperative_flow() -> None:
    source = '''
flow "demo":
  ai:
    model is "gpt-4"
    prompt is "Summarise: {state.input.text}"
    dataset is "summary_examples"
  return "ok"
'''.lstrip()
    program = parse_program(source)
    flow = program.flows[0]
    assert flow.ai_metadata is not None
    assert flow.ai_metadata.model == "gpt-4"
    assert flow.ai_metadata.prompt == "Summarise: {state.input.text}"
    assert flow.ai_metadata.dataset == "summary_examples"


def test_parse_ai_block_declarative_flow() -> None:
    source = '''
flow "demo"
  ai:
    model is "gpt-4"
    prompt is "Classify: {state.input.text}"
  input
    text is text
'''.lstrip()
    program = parse_program(source)
    flow = program.flows[0]
    assert flow.declarative is True
    assert flow.ai_metadata is not None
    assert flow.ai_metadata.model == "gpt-4"
    assert flow.ai_metadata.prompt == "Classify: {state.input.text}"
    assert flow.ai_metadata.dataset is None


def test_ai_block_missing_prompt_errors() -> None:
    source = '''
flow "demo":
  ai:
    model is "gpt-4"
  return "ok"
'''.lstrip()
    with pytest.raises(Namel3ssError) as exc:
        parse_program(source)
    assert "AI block requires a prompt" in str(exc.value)
