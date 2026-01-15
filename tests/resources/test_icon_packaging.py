from __future__ import annotations

from pathlib import Path


ICON_DIRS = (
    "actions",
    "navigation",
    "status",
    "tools",
    "data",
)


def test_icon_directories_exist() -> None:
    base = Path("resources/icons")
    assert base.is_dir()
    for name in ICON_DIRS:
        assert (base / name).is_dir()


def test_icon_packaging_config() -> None:
    manifest = Path("MANIFEST.in").read_text(encoding="utf-8")
    assert "recursive-include resources/icons *" in manifest

    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
    for name in ICON_DIRS:
        assert f'\"resources/icons/{name}\"' in pyproject
        assert f"resources/icons/{name}/*" in pyproject
