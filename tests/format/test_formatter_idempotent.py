from namel3ss.format.formatter import format_source


def test_formatter_idempotent():
    source = 'spec is "1.0"\n\nflow "demo":\n  return "ok"\n'
    once = format_source(source)
    twice = format_source(once)
    assert once == twice
