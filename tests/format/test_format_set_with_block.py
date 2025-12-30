from __future__ import annotations

from namel3ss.format import format_source


def test_formatter_preserves_set_with_block():
    source = (
        'spec is "1.0"\n\n'
        'flow "demo":\n'
        "  set state.order with:\n"
        '    order_id is "O-1"\n'
        '    customer is "Acme"\n'
    )
    assert format_source(source) == source
