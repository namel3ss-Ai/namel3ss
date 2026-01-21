from namel3ss.format.formatter import format_source


def test_formatter_inline_list_when_short():
    source = '''flow "demo":
  let roles is list of text:
    "admin"
    "staff"
'''
    formatted = format_source(source)
    assert 'let roles is list of text: "admin", "staff"' in formatted


def test_formatter_block_list_when_long():
    source = '''flow "demo":
  let roles is list of text:
    "role_with_a_really_long_name_one"
    "role_with_a_really_long_name_two"
'''
    formatted = format_source(source)
    assert "let roles is list of text:" in formatted
    assert '"role_with_a_really_long_name_one",' in formatted
    assert '"role_with_a_really_long_name_two",' in formatted


def test_formatter_removes_bracket_one_of_lists():
    source = '''identity "user":
  field "role" is text
  trust_level is one of ["guest", "member"]
'''
    formatted = format_source(source)
    assert "trust_level is one of \"guest\", \"member\"" in formatted
    assert "[" not in formatted
    assert "]" not in formatted
