from __future__ import annotations

from namel3ss.format import format_source


def test_formatter_preserves_exponent_operator():
    source = (
        'spec is "1.0"\n\n'
        'flow "demo":\n'
        "  return 2 ** 3\n"
    )
    assert format_source(source) == source


def test_formatter_exponent_idempotent():
    source = (
        'spec is "1.0"\n\n'
        'flow "demo":\n'
        "  return -2 ** 2\n"
    )
    once = format_source(source)
    assert once == source
    assert format_source(once) == once
