from __future__ import annotations

import json
from pathlib import Path

from namel3ss.cli.app_loader import load_program
from namel3ss.config.loader import load_config
from namel3ss.studio.api import get_ui_payload
from namel3ss.studio.session import SessionState
from namel3ss.validation import ValidationWarning
from namel3ss.validation_entrypoint import build_static_manifest


FIXTURE_PATH = Path("tests/fixtures/media_manifest_golden.json")
SOURCE = '''spec is "1.0"

page "home":
  image is "welcome":
    role is "hero"
  story "Onboarding":
    step "Start":
      image is "missing"
'''


def test_media_manifest_matches_golden(tmp_path: Path) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text(SOURCE, encoding="utf-8")
    media_root = tmp_path / "media"
    media_root.mkdir()
    (media_root / "welcome.png").write_text("image", encoding="utf-8")
    program, _ = load_program(app_path.as_posix())
    config = load_config(app_path=app_path, root=tmp_path)
    warnings: list[ValidationWarning] = []
    manifest = build_static_manifest(program, config=config, state={}, store=None, warnings=warnings)
    expected = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert manifest == expected
    assert warnings
    assert warnings[0].code == "media.missing"


def test_media_manifest_matches_studio_payload(tmp_path: Path) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text(SOURCE, encoding="utf-8")
    media_root = tmp_path / "media"
    media_root.mkdir()
    (media_root / "welcome.png").write_text("image", encoding="utf-8")
    program, _ = load_program(app_path.as_posix())
    config = load_config(app_path=app_path, root=tmp_path)
    warnings: list[ValidationWarning] = []
    manifest = build_static_manifest(program, config=config, state={}, store=None, warnings=warnings)
    studio_payload = get_ui_payload(SOURCE, SessionState(), app_path=app_path.as_posix())
    assert studio_payload.get("pages") == manifest.get("pages")
    assert studio_payload.get("actions") == manifest.get("actions")
    assert studio_payload.get("theme") == manifest.get("theme")
    assert studio_payload.get("ui") == manifest.get("ui")
