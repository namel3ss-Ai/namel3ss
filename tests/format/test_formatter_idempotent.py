from namel3ss.format.formatter import format_source


def test_formatter_idempotent():
    source = 'flow "demo":\n  return "ok"\n'
    once = format_source(source)
    twice = format_source(once)
    assert once == twice
