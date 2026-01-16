from __future__ import annotations

import re
from pathlib import Path


ICON_ROOT = Path("resources/icons")
BAD_PATTERNS = [
    re.compile(r'fill\s*=\s*"#', re.IGNORECASE),
    re.compile(r'stroke\s*=\s*"#', re.IGNORECASE),
    re.compile(r"rgba\(", re.IGNORECASE),
    re.compile(r"<style", re.IGNORECASE),
]


def _svg_files():
    assert ICON_ROOT.exists(), "resources/icons is missing"
    return sorted(p for p in ICON_ROOT.rglob("*") if p.is_file())


def test_only_svg_and_utf8():
    for path in _svg_files():
        assert path.suffix == ".svg", f"Non-SVG file found: {path}"
        text = path.read_text(encoding="utf-8")
        assert "currentColor" in text, f"Icon missing currentColor tint hook: {path.name}"


def test_icons_have_no_baked_colors():
    for path in _svg_files():
        text = path.read_text(encoding="utf-8")
        for pattern in BAD_PATTERNS:
            assert not pattern.search(text), f"Baked color found in {path}"
