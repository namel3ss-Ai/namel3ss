from __future__ import annotations

from namel3ss.errors.runtime.model import ErrorPack, RuntimeWhere


def render_error_plain(pack: ErrorPack) -> str:
    lines: list[str] = []
    what = pack.error.what or "runtime error"
    lines.append(f"error: {what}")

    lines.append("")
    lines.append("What happened")
    lines.extend(_bullet_lines([pack.error.what]))

    lines.append("")
    lines.append("Why")
    lines.extend(_bullet_lines(list(pack.error.why)))

    lines.append("")
    lines.append("How to fix")
    lines.extend(_bullet_lines(list(pack.error.fix)))

    lines.append("")
    lines.append("Where")
    lines.extend(_where_lines(pack.error.where))

    lines.append("")
    lines.append("Error id")
    lines.extend(_bullet_lines([pack.error.error_id]))

    return "\n".join(lines)


def render_fix_text(pack: ErrorPack) -> str:
    lines: list[str] = []
    lines.append("Fix this error")

    lines.append("")
    lines.append("How to fix")
    lines.extend(_bullet_lines(list(pack.error.fix)))

    lines.append("")
    lines.append("Why")
    lines.extend(_bullet_lines(list(pack.error.why)))

    lines.append("")
    lines.append("Error id")
    lines.extend(_bullet_lines([pack.error.error_id]))

    return "\n".join(lines)


def _bullet_lines(items: list[str | None]) -> list[str]:
    cleaned = [item for item in items if item]
    if not cleaned:
        return ["- none recorded"]
    return [f"- {item}" for item in cleaned]


def _where_lines(where: RuntimeWhere) -> list[str]:
    parts: list[str] = []
    if where.flow_name:
        parts.append(f"flow: {where.flow_name}")
    if where.statement_kind:
        parts.append(f"statement: {where.statement_kind}")
    if where.statement_index is not None:
        parts.append(f"statement index: {where.statement_index}")
    if where.line is not None:
        parts.append(f"line: {where.line}")
    if where.column is not None:
        parts.append(f"column: {where.column}")
    return _bullet_lines(parts)


__all__ = ["render_error_plain", "render_fix_text"]
