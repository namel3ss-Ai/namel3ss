from namel3ss.format.formatter import format_source


def test_formatter_normalizes_indentation():
    source = 'spec is "1.0"\n\nflow "demo":\n    return "ok"\n'
    formatted = format_source(source)
    assert formatted == 'spec is "1.0"\n\nflow "demo":\n  return "ok"\n'
