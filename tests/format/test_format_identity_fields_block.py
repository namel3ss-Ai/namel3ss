from namel3ss.format.formatter import format_source


def test_formatter_identity_fields_block():
    source = '''identity "user":
  field "subject" is text must be present
  field "role" is text
'''
    formatted = format_source(source)
    assert "fields:" in formatted
    assert "subject is text must be present" in formatted
    assert "role is text" in formatted
    assert 'field "subject"' not in formatted
