from __future__ import annotations

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.ui.manifest import build_manifest
from namel3ss.ui.presets import UI_PRESETS
from namel3ss.ui.settings import UI_FIELD_ORDER
from tests.conftest import lower_ir_program


def test_ui_preset_expands_deterministically():
    source = 'ui:\n  preset is "calm"\npage "home":\n  title is "Hi"\n'
    program = lower_ir_program(source)
    manifest_one = build_manifest(program, state={}, store=None)
    manifest_two = build_manifest(program, state={}, store=None)
    settings = manifest_one["ui"]["settings"]
    assert settings == manifest_two["ui"]["settings"]
    assert list(settings.keys()) == list(UI_FIELD_ORDER) + ["preset"]
    for key, value in UI_PRESETS["calm"].items():
        assert settings[key] == value
    assert settings["preset"] == "calm"


def test_ui_preset_overrides_win():
    source = '''ui:
  preset is "focus"
  density is "spacious"
  accent color is "teal"
page "home":
  title is "Hi"
'''
    manifest = build_manifest(lower_ir_program(source), state={}, store=None)
    settings = manifest["ui"]["settings"]
    assert settings["density"] == "spacious"
    assert settings["accent_color"] == "teal"
    assert settings["theme"] == UI_PRESETS["focus"]["theme"]
    assert settings["preset"] == "focus"


def test_ui_preset_unknown_suggests_fix():
    source = 'ui:\n  preset is "clarit"\npage "home":\n  title is "Hi"\n'
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    message = str(exc.value)
    assert "Unknown ui preset 'clarit'" in message
    assert 'Did you mean "clarity"' in message
