"""Tests for icon asset integrity.

Enforces:
- All files in resources/icons are valid UTF-8 SVG files
- No baked colors (fill="#...", stroke="#...", rgba())
- Filenames are lowercase snake_case
"""
from __future__ import annotations

import re
from pathlib import Path


ICONS_ROOT = Path("resources/icons")
BAKED_COLOR_PATTERN = re.compile(r'fill="#[0-9a-fA-F]|stroke="#[0-9a-fA-F]|rgba\(')
VALID_FILENAME_PATTERN = re.compile(r'^[a-z][a-z0-9_]*\.svg$')


def _icon_files() -> list[Path]:
    if not ICONS_ROOT.exists():
        return []
    return sorted(ICONS_ROOT.rglob("*.svg"))


def test_icons_are_valid_utf8_svg() -> None:
    """All icon files must be valid UTF-8 text."""
    for path in _icon_files():
        try:
            content = path.read_text(encoding="utf-8")
            assert content.strip().startswith("<svg") or content.strip().startswith("<?xml"), (
                f"{path} is not a valid SVG file"
            )
        except UnicodeDecodeError:
            raise AssertionError(f"{path} is not valid UTF-8")


def test_icons_have_no_baked_colors() -> None:
    """Icons must use currentColor, not hardcoded hex or rgba colors."""
    violations = []
    for path in _icon_files():
        content = path.read_text(encoding="utf-8")
        if BAKED_COLOR_PATTERN.search(content):
            violations.append(path.as_posix())
    assert not violations, f"Icons with baked colors: {violations}"


def test_icon_filenames_are_snake_case() -> None:
    """All icon filenames must be lowercase snake_case."""
    violations = []
    for path in _icon_files():
        if not VALID_FILENAME_PATTERN.match(path.name):
            violations.append(path.as_posix())
    assert not violations, f"Invalid icon filenames: {violations}"


def test_no_non_svg_files_in_icon_folders() -> None:
    """Only SVG files should exist in icon category folders."""
    if not ICONS_ROOT.exists():
        return
    violations = []
    for path in ICONS_ROOT.rglob("*"):
        if path.is_file() and not path.name.startswith("_") and path.suffix != ".svg":
            violations.append(path.as_posix())
    assert not violations, f"Non-SVG files in icons folder: {violations}"
