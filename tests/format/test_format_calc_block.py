from __future__ import annotations

from namel3ss.format import format_source


def test_formatter_preserves_calc_blocks() -> None:
    source = (
        'spec is "1.0"\n\n'
        'flow "demo":\n'
        "  let numbers is list:\n"
        "    1\n"
        "    2\n"
        "    3\n"
        "    10\n"
        "  calc:\n"
        "    doubled = map numbers with item as n:\n"
        "      n * 2\n"
        "    big = filter doubled with item as x:\n"
        "      x is greater than 5\n"
        "    state.total = reduce big with acc as s and item as v starting 0:\n"
        "      s + v\n"
        "    state.avg = mean(big)\n"
        "  return map:\n"
        '    "total" is state.total\n'
        '    "avg" is state.avg\n'
    )
    expected = (
        'spec is "1.0"\n\n'
        'flow "demo":\n'
        "  let numbers is list: 1, 2, 3, 10\n"
        "  calc:\n"
        "    doubled = map numbers with item as n:\n"
        "      n * 2\n"
        "    big = filter doubled with item as x:\n"
        "      x is greater than 5\n"
        "    state.total = reduce big with acc as s and item as v starting 0:\n"
        "      s + v\n"
        "    state.avg = mean(big)\n"
        "  return map:\n"
        '    "total" is state.total\n'
        '    "avg" is state.avg\n'
    )
    once = format_source(source)
    assert once == expected
    assert format_source(once) == expected
