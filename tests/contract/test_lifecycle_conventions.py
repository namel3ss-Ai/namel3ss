from __future__ import annotations

from pathlib import Path

DOC_PATH = Path("docs/runtime.md")
CANONICAL_VALUES = ["starting", "loading", "ready", "error", "stopped"]


def _extract_lifecycle_values(text: str) -> list[str]:
    lines = text.splitlines()
    try:
        start = lines.index("Canonical values:")
    except ValueError:
        return []
    values: list[str] = []
    for line in lines[start + 1 :]:
        if not line.strip():
            break
        if line.strip().startswith("Example:"):
            break
        if not line.strip().startswith("-"):
            continue
        raw = line.strip().lstrip("- ").strip()
        if raw.startswith('"') and raw.endswith('"'):
            raw = raw[1:-1]
        values.append(raw)
    return values


def test_lifecycle_conventions_are_canonical() -> None:
    assert DOC_PATH.exists(), "docs/runtime.md must exist"
    text = DOC_PATH.read_text(encoding="utf-8")
    values = _extract_lifecycle_values(text)
    assert values == CANONICAL_VALUES


def test_lifecycle_example_uses_canonical_state_path() -> None:
    text = DOC_PATH.read_text(encoding="utf-8")
    assert 'state:' in text
    assert 'lifecycle is "starting"' in text
    assert 'set state.lifecycle to "loading"' in text
    assert 'set state.lifecycle to "ready"' in text
