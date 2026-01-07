from __future__ import annotations

from namel3ss.format import format_source


def test_formatter_preserves_between_syntax():
    source = (
        'spec is "1.0"\n\n'
        'flow "demo":\n'
        "  if value is between min_val and max_val:\n"
        "    return true\n"
        "  return false\n"
    )
    assert format_source(source) == source


def test_formatter_preserves_strictly_between_syntax():
    source = (
        'spec is "1.0"\n\n'
        'flow "demo":\n'
        "  if value is strictly between min_val and max_val:\n"
        "    return true\n"
        "  return false\n"
    )
    once = format_source(source)
    assert once == source
    assert format_source(once) == once
