from __future__ import annotations

from pathlib import Path

import pytest

from namel3ss.cli.app_loader import load_program
from namel3ss.config.loader import load_config
from namel3ss.errors.base import Namel3ssError
from namel3ss.media import MediaValidationMode
from namel3ss.ui.manifest import build_manifest
from namel3ss.validation import ValidationMode, ValidationWarning
from namel3ss.validation_entrypoint import build_static_manifest


SOURCE = '''spec is "1.0"

page "home":
  image is "welcom"
'''


def _write_app(tmp_path: Path) -> Path:
    app_path = tmp_path / "app.ai"
    app_path.write_text(SOURCE, encoding="utf-8")
    return app_path


def _write_media(tmp_path: Path, names: list[str]) -> None:
    media_root = tmp_path / "media"
    media_root.mkdir()
    for name in names:
        (media_root / f"{name}.png").write_text("media", encoding="utf-8")


def test_missing_media_warns_in_check_mode(tmp_path: Path) -> None:
    app_path = _write_app(tmp_path)
    _write_media(tmp_path, ["welcome"])
    program, _ = load_program(app_path.as_posix())
    config = load_config(app_path=app_path, root=tmp_path)
    warnings: list[ValidationWarning] = []
    manifest = build_static_manifest(program, config=config, state={}, store=None, warnings=warnings)
    assert warnings
    warn = warnings[0]
    assert warn.code == "media.missing"
    assert "welcome" in (warn.fix or "")
    image = manifest["pages"][0]["elements"][0]
    assert image["media_name"] == "welcom"
    assert image["missing"] is True
    assert "fix_hint" in image


def test_missing_media_errors_in_build_mode(tmp_path: Path) -> None:
    app_path = _write_app(tmp_path)
    _write_media(tmp_path, ["welcome"])
    program, _ = load_program(app_path.as_posix())
    config = load_config(app_path=app_path, root=tmp_path)
    with pytest.raises(Namel3ssError) as excinfo:
        build_static_manifest(
            program,
            config=config,
            state={},
            store=None,
            warnings=[],
            media_mode=MediaValidationMode.BUILD,
        )
    assert "missing media" in str(excinfo.value).lower()


def test_runtime_placeholder_intent_for_missing_media(tmp_path: Path) -> None:
    app_path = _write_app(tmp_path)
    program, _ = load_program(app_path.as_posix())
    manifest = build_manifest(program, state={}, store=None, mode=ValidationMode.RUNTIME)
    image = manifest["pages"][0]["elements"][0]
    assert image["missing"] is True
    assert "media/" in image["fix_hint"]
