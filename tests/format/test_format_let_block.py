from __future__ import annotations

from namel3ss.format import format_source


def test_formatter_preserves_let_block_multiline():
    source = (
        'spec is "1.0"\n\n'
        'flow "demo":\n'
        "  let:\n"
        "    a is 10\n"
        "    b is 5\n"
        "    c is a + b\n"
    )
    assert format_source(source) == source


def test_formatter_preserves_let_block_inline_idempotent():
    source = (
        'spec is "1.0"\n\n'
        'flow "demo":\n'
        "  let:\n"
        "    a is 10, b is 5, c is a + b\n"
    )
    once = format_source(source)
    assert once == source
    assert format_source(once) == once
