from namel3ss.format.formatter import format_source


def test_formatter_keeps_tool_fields_plain():
    source = '''tool "greeter":
  input:
    name is text
    full name is text
  output:
    ok is boolean
'''
    formatted = format_source(source)
    assert "input:" in formatted
    assert "name is text" in formatted
    assert "full name is text" in formatted
    assert "output:" in formatted
    assert "ok is boolean" in formatted
    assert 'field "name"' not in formatted
