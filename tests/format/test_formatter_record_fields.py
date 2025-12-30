from namel3ss.format.formatter import format_source


def test_formatter_fields_use_is_and_fields_block():
    source = (
        'record "User":\n'
        "  email string must be present\n"
        "  age int must be greater than 17\n"
        "  bio string must have length at least 3\n"
    )
    formatted = format_source(source)
    assert "fields:" in formatted
    assert "email is text must be present" in formatted
    assert "age is number must be greater than 17" in formatted
    assert "bio is text must have length at least 3" in formatted
    assert 'field "email"' not in formatted
    assert " email string " not in formatted
