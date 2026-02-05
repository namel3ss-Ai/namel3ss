from __future__ import annotations

import pytest

from namel3ss.errors.base import Namel3ssError
from tests.conftest import lower_ir_program


def test_lower_ai_flows_and_prompts() -> None:
    source = '''
record "Note":
  id number

prompt "summary_prompt":
  version is "1.0.0"
  text is "Summarise the input."

llm_call "summarise":
  model is "gpt-4"
  prompt is "summary_prompt"
  output is text
  return "ok"
'''.lstrip()
    program = lower_ir_program(source)
    assert len(program.prompts) == 1
    assert program.prompts[0].name == "summary_prompt"
    assert len(program.ai_flows) == 1
    ai_flow = program.ai_flows[0]
    assert ai_flow.kind == "llm_call"
    assert ai_flow.output_type == "text"
    flow = next(flow for flow in program.flows if flow.name == "summarise")
    assert flow.ai_metadata is not None
    assert flow.ai_metadata.kind == "llm_call"


def test_crud_unknown_record_errors() -> None:
    source = '''
crud "Missing"
'''.lstrip()
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert exc.value.message == (
        'What happened: Crud references unknown record "Missing".\n'
        "Why: Crud can only target records that are defined.\n"
        "Fix: Add the record declaration or update the crud name.\n"
        'Example: record "Missing":'
    )


def test_prompt_reference_missing_errors() -> None:
    source = '''
llm_call "summarise":
  model is "gpt-4"
  prompt is "summary_prompt"
  output is text
'''.lstrip()
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert exc.value.message == (
        'What happened: Prompt "summary_prompt" is not defined.\n'
        "Why: Prompt references must match a prompt declaration.\n"
        "Fix: Add a prompt block with that name or use a longer prompt string.\n"
        'Example: prompt "summary_prompt":\n'
        '  version is "1.0.0"\n'
        '  text is "Summarise the input."'
    )
