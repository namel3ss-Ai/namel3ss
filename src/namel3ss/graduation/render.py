from __future__ import annotations

from namel3ss.graduation.rules import GraduationReport


def render_summary_lines(matrix: dict) -> list[str]:
    summary = matrix.get("summary") or {}
    total = summary.get("total") or 0
    lines = [f"Total capabilities {total}"]
    for entry in summary.get("by_status") or []:
        status = entry.get("status") or ""
        count = entry.get("count") or 0
        lines.append(f"{status} {count}")
    return _clean_lines(lines)


def render_matrix_lines(matrix: dict) -> list[str]:
    lines: list[str] = []
    for item in matrix.get("capabilities") or []:
        cap_id = item.get("id") or ""
        title = item.get("title") or ""
        status = item.get("status") or ""
        lines.append(f"{cap_id} {status} {title}")
    return _clean_lines(lines)


def render_graduation_lines(report: GraduationReport) -> list[str]:
    ai_ready = _bool_label(report.ai_language_ready)
    beta_ready = _bool_label(report.beta_ready)
    lines = [
        f"AI language ready {ai_ready}",
        f"Beta ready {beta_ready}",
    ]
    if report.missing_ai_language:
        missing = ", ".join(report.missing_ai_language)
        lines.append(f"Missing for AI language {missing}")
    if report.missing_beta:
        missing = ", ".join(report.missing_beta)
        lines.append(f"Missing for beta {missing}")
    return _clean_lines(lines)


def _clean_lines(lines: list[str]) -> list[str]:
    cleaned: list[str] = []
    for line in lines:
        text = " ".join(str(line).split()).strip()
        if text:
            cleaned.append(text)
    return cleaned


def _bool_label(value: bool) -> str:
    return "yes" if value else "no"


__all__ = ["render_graduation_lines", "render_matrix_lines", "render_summary_lines"]
