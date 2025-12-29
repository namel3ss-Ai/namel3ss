from __future__ import annotations


def wake_up_title() -> str:
    return "Memory wake up report"


def wake_up_lines(
    *,
    restored: bool,
    total_items: int,
    team_items: int,
    active_rules: int,
    pending_proposals: int,
    pending_handoffs: int,
    cache_entries: int,
    cache_enabled: bool,
) -> list[str]:
    lines: list[str] = []
    lines.append("Memory was restored." if restored else "Memory is new.")
    if total_items <= 0:
        lines.append("No memory items yet.")
    else:
        lines.append(f"Total items are {total_items}.")
    if team_items > 0:
        lines.append("Team memory loaded.")
    else:
        lines.append("Team memory is empty.")
    if active_rules > 0:
        lines.append(f"{_count_words(active_rules)} rules active.")
    else:
        lines.append("No active rules.")
    if pending_proposals > 0:
        lines.append(f"{_count_words(pending_proposals)} proposals still waiting.")
    else:
        lines.append("No proposals are waiting.")
    if pending_handoffs > 0:
        lines.append(f"{_count_words(pending_handoffs)} handoffs still waiting.")
    else:
        lines.append("No handoffs are waiting.")
    if cache_enabled:
        if cache_entries <= 0:
            lines.append("Cache is empty.")
        elif cache_entries == 1:
            lines.append("Cache has one entry.")
        else:
            lines.append(f"Cache has {cache_entries} entries.")
    else:
        lines.append("Cache is off.")
    return lines


def restore_failed_title() -> str:
    return "Memory restore failed"


def restore_failed_lines(*, reason: str, detail: str | None = None) -> list[str]:
    lines = ["Memory restore failed."]
    if reason:
        lines.append(reason)
    if detail:
        lines.append(detail)
    return lines


def _count_words(value: int) -> str:
    mapping = {
        0: "Zero",
        1: "One",
        2: "Two",
        3: "Three",
        4: "Four",
        5: "Five",
        6: "Six",
        7: "Seven",
        8: "Eight",
        9: "Nine",
        10: "Ten",
        11: "Eleven",
        12: "Twelve",
    }
    return mapping.get(value, str(value))


__all__ = ["restore_failed_lines", "restore_failed_title", "wake_up_lines", "wake_up_title"]
