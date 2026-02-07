from __future__ import annotations

from namel3ss.format.formatter import format_source


def test_formatter_expands_bracket_lists_to_indented_blocks() -> None:
    source = '''classification "tag_message":
  model is "gpt-4"
  prompt is "Tag"
  labels: [billing, technical, "general"]
'''
    formatted = format_source(source)
    assert "labels:" in formatted
    assert "  billing" in formatted
    assert '  "general"' in formatted
    assert "[billing" not in formatted


def test_formatter_expands_braced_record_and_fields_blocks() -> None:
    source = '''record "User": { id number, name text }

record "Order":
  fields: { order_id is text, total is number }
'''
    formatted = format_source(source)
    assert 'record "User":' in formatted
    assert "fields:" in formatted
    assert "id number" in formatted
    assert "name text" in formatted
    assert "order_id is text" in formatted
    assert "total is number" in formatted
    assert "{" not in formatted
    assert "}" not in formatted


def test_formatter_expands_multiline_grouping_forms() -> None:
    source = '''record "User": {
  id number,
  name text
}

classification "tag_message":
  model is "gpt-4"
  prompt is "Tag"
  labels: [
    billing,
    technical
  ]
'''
    formatted = format_source(source)
    assert 'record "User":' in formatted
    assert "  id number" in formatted
    assert "name text" in formatted or "name is text" in formatted
    assert "labels:" in formatted
    assert "  billing" in formatted
    assert "  technical" in formatted
    assert "labels: [" not in formatted


def test_formatter_preserves_empty_grouping_forms() -> None:
    source = '''capabilities: []
record "User": {}
'''
    formatted = format_source(source)
    assert "capabilities: []" in formatted
    assert 'record "User": {}' in formatted
