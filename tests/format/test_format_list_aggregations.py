from __future__ import annotations

from namel3ss.format import format_source


def test_formatter_preserves_list_aggregations() -> None:
    source = (
        'spec is "1.0"\n\n'
        'flow "demo":\n'
        "  let numbers is list:\n"
        "    10\n"
        "    20\n"
        "  let total is sum(numbers)\n"
        "  let avg is mean(numbers)\n"
        "  let mid is median(numbers)\n"
        "  return max(numbers)\n"
    )
    once = format_source(source)
    assert once == source
    assert format_source(once) == once
