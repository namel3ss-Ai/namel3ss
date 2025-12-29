from __future__ import annotations

from namel3ss.outcome.model import OutcomePack


def render_what(pack: OutcomePack) -> str:
    lines: list[str] = []
    lines.append("run outcome")

    lines.append("")
    lines.append("Status")
    lines.extend(_bullet_lines([pack.outcome.status]))

    lines.append("")
    lines.append("Store")
    lines.extend(
        _kv_bullets(
            {
                "began": _yes_no(pack.outcome.store.began),
                "committed": _yes_no(pack.outcome.store.committed),
                "commit_failed": _yes_no(pack.outcome.store.commit_failed),
                "rolled_back": _yes_no(pack.outcome.store.rolled_back),
                "rollback_failed": _yes_no(pack.outcome.store.rollback_failed),
            }
        )
    )

    lines.append("")
    lines.append("State")
    lines.extend(
        _kv_bullets(
            {
                "loaded_from_store": _yes_no(pack.outcome.state.loaded_from_store),
                "save_attempted": _yes_no(pack.outcome.state.save_attempted),
                "save_succeeded": _yes_no(pack.outcome.state.save_succeeded),
                "save_failed": _yes_no(pack.outcome.state.save_failed),
            }
        )
    )

    lines.append("")
    lines.append("Memory")
    lines.extend(
        _kv_bullets(
            {
                "persist_attempted": _yes_no(pack.outcome.memory.persist_attempted),
                "persist_succeeded": _yes_no(pack.outcome.memory.persist_succeeded),
                "persist_failed": _yes_no(pack.outcome.memory.persist_failed),
                "skipped_reason": pack.outcome.memory.skipped_reason or "none recorded",
            }
        )
    )

    lines.append("")
    lines.append("What did not happen")
    lines.extend(_bullet_lines(list(pack.outcome.what_did_not_happen)))

    return "\n".join(lines)


def _bullet_lines(items: list[str]) -> list[str]:
    cleaned = [item for item in items if item]
    if not cleaned:
        return ["- none recorded"]
    return [f"- {item}" for item in cleaned]


def _kv_bullets(items: dict[str, str]) -> list[str]:
    return [f"- {key}: {value}" for key, value in items.items()]


def _yes_no(value: bool | None) -> str:
    if value is None:
        return "unknown"
    return "yes" if value else "no"


__all__ = ["render_what"]
