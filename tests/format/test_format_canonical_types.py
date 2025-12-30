from namel3ss.format.formatter import format_source


def test_formatter_rewrites_aliases_to_canonical():
    src = '''
record "User":
  field "name" is string must be present
  field "age" is int
  field "active" is bool
'''
    formatted = format_source(src)
    assert "fields:" in formatted
    assert "name is text" in formatted
    assert "age is number" in formatted
    assert "active is boolean" in formatted


def test_formatter_is_idempotent():
    src = '''
record "User":
  field "name" is string
'''
    once = format_source(src)
    twice = format_source(once)
    assert once == twice
