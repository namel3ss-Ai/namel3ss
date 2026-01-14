from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.lang.keywords import reserved_keywords


def run_reserved_command(args: list[str]) -> int:
    if args:
        raise Namel3ssError("The 'reserved' command does not take arguments.")
    words = reserved_keywords()
    lines = [
        "Reserved words in namel3ss (cannot be used as variable names):",
        "",
        *[f"- {word}" for word in words],
        "Tip: use a prefix like `ticket_title`, `item_type`, etc.",
    ]
    print("\n".join(lines))
    return 0


__all__ = ["run_reserved_command"]
