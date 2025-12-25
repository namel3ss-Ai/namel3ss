from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.packs.layout import pack_intent_path


REQUIRED_INTENT_HEADINGS = [
    "What this pack does",
    "Tools provided (English)",
    "Inputs/outputs summary",
    "Capabilities & risk",
    "Failure modes",
    "Runner requirements",
]


@dataclass(frozen=True)
class IntentSummary:
    headings: list[str]
    missing: list[str]
    failure_modes: str | None


def load_intent(pack_dir: Path) -> str:
    path = pack_intent_path(pack_dir)
    if not path.exists():
        raise Namel3ssError(_missing_intent_message(path))
    return path.read_text(encoding="utf-8")


def summarize_intent(text: str) -> IntentSummary:
    headings = _extract_headings(text)
    missing = [heading for heading in REQUIRED_INTENT_HEADINGS if _normalize_heading(heading) not in headings]
    failure_modes = _section_body(text, "Failure modes")
    if failure_modes is not None:
        failure_modes = failure_modes.strip() or None
    return IntentSummary(
        headings=[_normalize_heading(value) for value in headings],
        missing=missing,
        failure_modes=failure_modes,
    )


def validate_intent(text: str, path: Path) -> list[str]:
    summary = summarize_intent(text)
    if not summary.missing:
        return []
    return [_missing_headings_message(path, summary.missing)]


def _extract_headings(text: str) -> set[str]:
    headings: set[str] = set()
    for raw in text.splitlines():
        line = raw.strip()
        if not line.startswith("#"):
            continue
        heading = line.lstrip("#").strip()
        if heading:
            headings.add(_normalize_heading(heading))
    return headings


def _section_body(text: str, heading: str) -> str | None:
    normalized = _normalize_heading(heading)
    lines = text.splitlines()
    start = None
    for idx, raw in enumerate(lines):
        line = raw.strip()
        if not line.startswith("#"):
            continue
        found = _normalize_heading(line.lstrip("#").strip())
        if found == normalized:
            start = idx + 1
            break
    if start is None:
        return None
    body_lines: list[str] = []
    for raw in lines[start:]:
        if raw.strip().startswith("#"):
            break
        body_lines.append(raw)
    return "\n".join(body_lines)


def _normalize_heading(text: str) -> str:
    return " ".join(text.lower().split())


def _missing_intent_message(path: Path) -> str:
    return build_guidance_message(
        what="Intent file is missing.",
        why=f"Expected {path.as_posix()} to exist.",
        fix="Add intent.md with the required headings.",
        example=_intent_example(),
    )


def _missing_headings_message(path: Path, missing: list[str]) -> str:
    return build_guidance_message(
        what="Intent file is missing required headings.",
        why=f"Missing headings: {', '.join(missing)}.",
        fix="Add the missing sections to intent.md.",
        example=_intent_example(),
    )


def _intent_example() -> str:
    return (
        "# Pack Intent\n"
        "## What this pack does\n"
        "## Tools provided (English)\n"
        "## Inputs/outputs summary\n"
        "## Capabilities & risk\n"
        "## Failure modes\n"
        "## Runner requirements\n"
    )


__all__ = ["IntentSummary", "REQUIRED_INTENT_HEADINGS", "load_intent", "summarize_intent", "validate_intent"]
