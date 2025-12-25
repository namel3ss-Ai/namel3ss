from __future__ import annotations

import re
from pathlib import Path


FORBIDDEN_PATTERNS = [
    re.compile(r"^\s*kind\s+is\b"),
    re.compile(r"^\s*entry\s+is\b"),
    re.compile(r"^\s*input_schema\s+is\b"),
    re.compile(r"^\s*output_schema\s+is\b"),
    re.compile(r"\bcall\s+tool\b"),
]


def _is_allowed_changelog_block(lines: list[str], index: int, allow_blocks: set[int]) -> bool:
    return index in allow_blocks


def _allowed_changelog_lines(lines: list[str]) -> set[int]:
    allowed: set[int] = set()
    pending = False
    in_block = False
    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped in {"Before:", "After:"}:
            pending = True
            continue
        if stripped.startswith("```"):
            if pending and not in_block:
                in_block = True
                pending = False
                continue
            if in_block:
                in_block = False
                continue
        if in_block:
            allowed.add(idx)
    return allowed


def _scan_lines(path: Path, lines: list[str], *, allow_lines: set[int] | None = None) -> list[tuple[str, int, str]]:
    offenders: list[tuple[str, int, str]] = []
    for idx, line in enumerate(lines, start=1):
        if allow_lines and idx in allow_lines:
            continue
        for pattern in FORBIDDEN_PATTERNS:
            if pattern.search(line):
                offenders.append((path.as_posix(), idx, line.rstrip("\n")))
                break
    return offenders


def test_no_legacy_tool_syntax_strings() -> None:
    root = Path(__file__).resolve().parents[2]
    offenders: list[tuple[str, int, str]] = []
    for path in root.rglob("*"):
        if path.is_dir():
            continue
        if path.suffix not in {".ai", ".md"}:
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        if path.name == "CHANGELOG.md":
            allowed = _allowed_changelog_lines(lines)
            offenders.extend(_scan_lines(path, lines, allow_lines=allowed))
        else:
            offenders.extend(_scan_lines(path, lines))
    assert not offenders, "Legacy tool syntax found:\n" + "\n".join(
        f"{path}:{line} | {text}" for path, line, text in offenders
    )
