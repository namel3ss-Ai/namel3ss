from __future__ import annotations

from namel3ss.format import format_source


def test_formatter_preserves_list_transform_blocks() -> None:
    source = (
        'spec is "1.0"\n\n'
        'flow "demo":\n'
        "  let numbers is list:\n"
        "    1\n"
        "    2\n"
        "  let doubled is map numbers with item as n:\n"
        "    n * 2\n"
        "  let big is filter doubled with item as x:\n"
        "    x is greater than 2\n"
        "  return big\n"
    )
    expected = (
        'spec is "1.0"\n\n'
        'flow "demo":\n'
        "  let numbers is list: 1, 2\n"
        "  let doubled is map numbers with item as n:\n"
        "    n * 2\n"
        "  let big is filter doubled with item as x:\n"
        "    x is greater than 2\n"
        "  return big\n"
    )
    once = format_source(source)
    assert once == expected
    assert format_source(once) == expected
