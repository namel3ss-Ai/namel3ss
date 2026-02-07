from __future__ import annotations

import pytest

from namel3ss.errors.base import Namel3ssError
from tests.conftest import parse_program


def test_classification_labels_bracket_list_parses() -> None:
    source = '''
classification "tag_message":
  model is "gpt-4"
  prompt is "Tag the message."
  labels: [billing, technical, "general"]
'''.lstrip()
    program = parse_program(source)
    flow = program.ai_flows[0]
    assert flow.labels == ["billing", "technical", "general"]


def test_rag_sources_bracket_list_parses() -> None:
    source = '''
rag "search_docs":
  model is "gpt-4"
  prompt is "Answer from docs."
  sources: [kb_docs, api_docs]
'''.lstrip()
    program = parse_program(source)
    flow = program.ai_flows[0]
    assert flow.sources == ["kb_docs", "api_docs"]


def test_record_braced_block_parses() -> None:
    source = '''
record "User": { id number, name text, email text }
'''.lstrip()
    program = parse_program(source)
    record = program.records[0]
    assert [field.name for field in record.fields] == ["id", "name", "email"]


def test_record_fields_braced_block_parses() -> None:
    source = '''
record "User":
  fields: { id is number, name is text }
'''.lstrip()
    program = parse_program(source)
    record = program.records[0]
    assert [field.name for field in record.fields] == ["id", "name"]


def test_pattern_parameters_braced_block_parses() -> None:
    source = '''
pattern "Notice":
  parameters: { heading is text, count is number optional }
  title is param.heading
'''.lstrip()
    program = parse_program(source)
    pattern = program.ui_patterns[0]
    assert [param.name for param in pattern.parameters] == ["heading", "count"]
    assert pattern.parameters[1].optional is True


def test_capabilities_bracket_list_parses() -> None:
    source = '''
capabilities: [http, jobs, files]

flow "demo":
  return "ok"
'''.lstrip()
    program = parse_program(source)
    assert program.capabilities == ["http", "jobs", "files"]


def test_empty_capabilities_bracket_list_parses() -> None:
    source = '''
capabilities: []

flow "demo":
  return "ok"
'''.lstrip()
    program = parse_program(source)
    assert program.capabilities == []


def test_packs_bracket_list_parses() -> None:
    source = '''
packs: ["builtin.text", "example.greeting"]

flow "demo":
  return "ok"
'''.lstrip()
    program = parse_program(source)
    assert getattr(program, "pack_allowlist", None) == ["builtin.text", "example.greeting"]


def test_empty_record_braced_block_parses() -> None:
    source = '''
record "User": {}
'''.lstrip()
    program = parse_program(source)
    record = program.records[0]
    assert record.fields == []


def test_empty_fields_braced_block_is_rejected() -> None:
    source = '''
record "User":
  fields: {}
'''.lstrip()
    with pytest.raises(Namel3ssError) as exc:
        parse_program(source)
    assert "has no fields" in exc.value.message.lower()


def test_empty_parameters_braced_block_is_rejected() -> None:
    source = '''
pattern "Notice":
  parameters: {}
  title is "x"
'''.lstrip()
    with pytest.raises(Namel3ssError) as exc:
        parse_program(source)
    assert "parameters block has no entries" in exc.value.message.lower()


def test_use_only_bracket_list_parses() -> None:
    source = '''
use module "modules/common.ai" as common
only: [functions, tools]

flow "demo":
  return "ok"
'''.lstrip()
    program = parse_program(source)
    use_decl = program.uses[0]
    assert use_decl.only == ["functions", "tools"]


def test_bracket_list_requires_commas() -> None:
    source = '''
classification "tag_message":
  model is "gpt-4"
  prompt is "Tag the message."
  labels: [billing technical]
'''.lstrip()
    with pytest.raises(Namel3ssError) as exc:
        parse_program(source)
    assert "comma-separated" in exc.value.message.lower()


def test_braced_block_requires_commas() -> None:
    source = '''
record "User": { id number name text }
'''.lstrip()
    with pytest.raises(Namel3ssError) as exc:
        parse_program(source)
    assert "comma-separated" in exc.value.message.lower()


def test_nested_grouping_is_rejected() -> None:
    source = '''
classification "tag_message":
  model is "gpt-4"
  prompt is "Tag the message."
  labels: [billing, {technical}]
'''.lstrip()
    with pytest.raises(Namel3ssError) as exc:
        parse_program(source)
    assert "nested grouping" in exc.value.message.lower()


def test_multiline_braced_block_is_rejected() -> None:
    source = '''
record "User": {
  id number,
  name text
}
'''.lstrip()
    with pytest.raises(Namel3ssError) as exc:
        parse_program(source)
    assert "cannot span multiple lines" in exc.value.message.lower()


def test_multiline_bracket_list_is_rejected() -> None:
    source = '''
classification "tag_message":
  model is "gpt-4"
  prompt is "Tag the message."
  labels: [
    billing,
    technical
  ]
'''.lstrip()
    with pytest.raises(Namel3ssError) as exc:
        parse_program(source)
    assert "cannot span multiple lines" in exc.value.message.lower()
