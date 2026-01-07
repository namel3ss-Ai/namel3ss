from __future__ import annotations

from namel3ss.format import format_source


def test_formatter_preserves_reduce_blocks() -> None:
    source = (
        'spec is "1.0"\n\n'
        'flow "demo":\n'
        "  let numbers is list:\n"
        "    1\n"
        "    2\n"
        "  let total is reduce numbers with acc as s and item as n starting 0:\n"
        "    s + n\n"
        "  return total\n"
    )
    once = format_source(source)
    assert once == source
    assert format_source(once) == once
