from __future__ import annotations

import pytest

from namel3ss.errors.base import Namel3ssError
from tests.conftest import parse_program


def test_parse_ai_flow_types() -> None:
    source = '''
prompt "summary_prompt":
  version is "1.0.0"
  text is "Summarise the input."

llm_call "summarise":
  model is "gpt-4"
  prompt is "summary_prompt"
  output is text
  return "ok"
'''.lstrip()
    program = parse_program(source)
    assert len(program.ai_flows) == 1
    ai_flow = program.ai_flows[0]
    assert ai_flow.name == "summarise"
    assert ai_flow.kind == "llm_call"
    assert ai_flow.output_type == "text"
    flow = next(flow for flow in program.flows if flow.name == "summarise")
    assert flow.ai_metadata is not None
    assert flow.ai_metadata.kind == "llm_call"


def test_classification_missing_labels_errors() -> None:
    source = '''
classification "tag_message":
  model is "gpt-4"
  prompt is "Tag the message."
'''.lstrip()
    with pytest.raises(Namel3ssError) as exc:
        parse_program(source)
    assert exc.value.message == "Classification flow is missing labels"
