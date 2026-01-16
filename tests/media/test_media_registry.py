from __future__ import annotations

from pathlib import Path

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.media import media_names, resolve_media_file


def test_media_names_are_deterministic(tmp_path: Path) -> None:
    media_root = tmp_path / "media"
    media_root.mkdir()
    (media_root / "b.png").write_text("b", encoding="utf-8")
    (media_root / "a.jpg").write_text("a", encoding="utf-8")
    names = media_names(root=media_root)
    assert names == tuple(sorted(names))


def test_media_registry_accepts_allowed_formats(tmp_path: Path) -> None:
    media_root = tmp_path / "media"
    media_root.mkdir()
    (media_root / "welcome.png").write_text("png", encoding="utf-8")
    (media_root / "hero.jpg").write_text("jpg", encoding="utf-8")
    (media_root / "logo.jpeg").write_text("jpeg", encoding="utf-8")
    (media_root / "icon.svg").write_text("<svg/>", encoding="utf-8")
    (media_root / "promo.webp").write_bytes(b"webp")
    names = set(media_names(root=media_root))
    assert names == {"welcome", "hero", "logo", "icon", "promo"}
    assert resolve_media_file("welcome", root=media_root) == media_root / "welcome.png"
    assert resolve_media_file("hero", root=media_root) == media_root / "hero.jpg"


def test_media_registry_rejects_disallowed_formats(tmp_path: Path) -> None:
    media_root = tmp_path / "media"
    media_root.mkdir()
    (media_root / "bad.gif").write_text("gif", encoding="utf-8")
    with pytest.raises(Namel3ssError) as excinfo:
        media_names(root=media_root)
    message = str(excinfo.value).lower()
    assert "allowed formats" in message
    assert "bad.gif" in message


def test_media_collision_lists_conflicts_in_order(tmp_path: Path) -> None:
    media_root = tmp_path / "media"
    media_root.mkdir()
    (media_root / "welcome.svg").write_text("<svg/>", encoding="utf-8")
    (media_root / "welcome.png").write_text("png", encoding="utf-8")
    with pytest.raises(Namel3ssError) as excinfo:
        media_names(root=media_root)
    message = str(excinfo.value)
    assert "welcome.png" in message
    assert "welcome.svg" in message
    assert message.index("welcome.png") < message.index("welcome.svg")
