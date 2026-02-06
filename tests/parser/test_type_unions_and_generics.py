from __future__ import annotations

from tests.conftest import parse_program


def test_record_parses_generics_and_union_types() -> None:
    source = '''
spec is "1.0"

record "Article" version "2.0":
  id number
  tags list<text>
  metadata map<text, text | number>
  published_at number | null
'''.lstrip()
    program = parse_program(source)
    record = program.records[0]
    assert getattr(record, "version", None) == "2.0"
    fields = {field.name: field.type_name for field in record.fields}
    assert fields["id"] == "number"
    assert fields["tags"] == "list<text>"
    assert fields["metadata"] == "map<text, text | number>"
    assert fields["published_at"] == "number | null"


def test_function_fields_parse_union_and_optional_types() -> None:
    source = '''
spec is "1.0"

define function "choose value":
  input:
    selected id is number | text
  output:
    display value is text optional
  return "ok"
'''.lstrip()
    program = parse_program(source)
    function = program.functions[0]
    assert function.signature.inputs[0].type_name == "number | text"
    assert function.signature.outputs[0].type_name == "text"
    assert function.signature.outputs[0].required is False
