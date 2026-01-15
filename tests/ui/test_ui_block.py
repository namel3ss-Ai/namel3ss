from __future__ import annotations

from pathlib import Path

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.module_loader import load_project
from namel3ss.studio.api import get_ui_payload
from namel3ss.studio.session import SessionState
from namel3ss.ui.manifest import build_manifest
from namel3ss.ui.settings import UI_ALLOWED_VALUES, UI_DEFAULTS, UI_FIELD_ORDER
from tests.conftest import lower_ir_program


def _ui_block_line(key: str, value: str) -> str:
    return f'  {key.replace("_", " ")} is "{value}"'


def test_ui_defaults_applied_when_missing():
    source = 'page "home":\n  title is "Hello"\n'
    program = lower_ir_program(source)
    manifest = build_manifest(program, state={}, store=None)
    assert manifest["ui"]["settings"] == {key: UI_DEFAULTS[key] for key in UI_FIELD_ORDER}
    assert manifest["theme"]["setting"] == UI_DEFAULTS["theme"]


def test_studio_payload_includes_ui_settings(tmp_path: Path):
    source = 'spec is "1.0"\n\npage "home":\n  title is "Hello"\n'
    app_file = tmp_path / "app.ai"
    app_file.write_text(source, encoding="utf-8")
    payload = get_ui_payload(source, SessionState(), app_path=app_file.as_posix())
    settings = (payload.get("ui") or {}).get("settings")
    assert settings == {key: UI_DEFAULTS[key] for key in UI_FIELD_ORDER}
    assert (payload.get("theme") or {}).get("setting") == UI_DEFAULTS["theme"]


def test_ui_accepts_all_allowed_values():
    base = ['ui:']
    for key, values in UI_ALLOWED_VALUES.items():
        for value in values:
            body = "\n".join(base + [_ui_block_line(key, value)]) + '\npage "home":\n  title is "Hi"\n'
            program = lower_ir_program(body)
            manifest = build_manifest(program, state={}, store=None)
            assert manifest["ui"]["settings"][key] == value


def test_ui_unknown_value_suggests_fix():
    source = 'ui:\n  theme is "lihgt"\npage "home":\n  title is "Hi"\n'
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    message = str(exc.value)
    assert "Unknown theme 'lihgt'" in message
    assert 'Did you mean "light"' in message


def test_ui_unknown_key_suggests_fix():
    source = 'ui:\n  acncent color is "blue"\npage "home":\n  title is "Hi"\n'
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    message = str(exc.value)
    assert "Unknown ui field 'acncent color'" in message
    assert 'Did you mean "accent color"' in message


def test_ui_order_normalized_deterministically():
    source_one = '''ui:
  motion is "none"
  theme is "dark"
  accent color is "green"
  shape is "square"
  surface is "outlined"
  density is "compact"
page "home":
  title is "Hi"
'''
    source_two = '''ui:
  density is "compact"
  surface is "outlined"
  shape is "square"
  accent color is "green"
  theme is "dark"
  motion is "none"
page "home":
  title is "Hi"
'''
    manifest_one = build_manifest(lower_ir_program(source_one), state={}, store=None)
    manifest_two = build_manifest(lower_ir_program(source_two), state={}, store=None)
    assert manifest_one["ui"]["settings"] == manifest_two["ui"]["settings"]
    assert list(manifest_one["ui"]["settings"].keys()) == list(UI_FIELD_ORDER)


def test_ui_static_validation_matches_cli_and_studio(tmp_path: Path):
    source = 'spec is "1.0"\n\nui:\n  theme is "lihgt"\npage "home":\n  title is "Hi"\n'
    app_file = tmp_path / "app.ai"
    app_file.write_text(source, encoding="utf-8")
    with pytest.raises(Namel3ssError) as exc:
        load_project(app_file)
    payload = get_ui_payload(source, SessionState(), app_path=app_file.as_posix())
    assert payload["ok"] is False
    assert payload.get("message") in str(exc.value)
