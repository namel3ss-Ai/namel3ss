from __future__ import annotations

from namel3ss.icons.registry import icon_names


def run_icons_command(args: list[str]) -> int:
    if args:
        print("Usage: n3 icons")
        return 1
    names = icon_names()
    lines = [
        "Built-in icons (cannot set custom colors; runtime tints them):",
        "",
        *[f"- {name}" for name in names],
        "Tip: pick an icon name and an optional tone; run `n3 check` to validate.",
    ]
    print("\n".join(lines))
    return 0


__all__ = ["run_icons_command"]
