from namel3ss.format.formatter import format_source


def test_formatter_normalizes_indentation():
    source = 'flow "demo":\n    return "ok"\n'
    formatted = format_source(source)
    assert formatted == 'flow "demo":\n  return "ok"\n'
