from namel3ss.format.formatter import format_source


def test_formatter_fields_use_is_and_field_keyword():
    source = (
        'record "User":\n'
        "  email string must be present\n"
        "  age int must be greater than 17\n"
        "  bio string must have length at least 3\n"
    )
    formatted = format_source(source)
    assert 'field "email" is string must be present' in formatted
    assert 'field "age" is int must be greater than 17' in formatted
    assert 'field "bio" is string must have length at least 3' in formatted
    assert " email string " not in formatted
