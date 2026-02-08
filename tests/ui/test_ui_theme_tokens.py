from __future__ import annotations

import hashlib

import pytest

from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.ui.manifest import build_manifest
from tests.conftest import lower_ir_program


def _hash_theme(theme: dict) -> str:
    payload = canonical_json_dumps(theme, pretty=False, drop_run_keys=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def test_ui_theme_tokens_compile_into_manifest_css() -> None:
    source = '''
ui:
  theme is "modern"
  primary_color is "#0055CC"
  secondary_color is "#5856D6"
  font_family is "Fira Sans"
  spacing_scale is 1.2
  border_radius is 6

page "home":
  title is "Hello"
'''
    manifest = build_manifest(lower_ir_program(source), state={}, store=None)
    theme = manifest["theme"]
    assert theme["theme_name"] == "modern"
    assert theme["tokens"]["primary_color"] == "#0055CC"
    assert theme["tokens"]["spacing_scale"] == 1.2
    assert theme["tokens"]["border_radius"] == 6
    assert isinstance(theme.get("css"), str) and "--n3-primary-color" in theme["css"]
    assert isinstance(theme.get("css_hash"), str) and len(theme["css_hash"]) == 64
    assert "font_url" in theme


def test_ui_style_theme_does_not_override_runtime_theme_setting() -> None:
    source = '''
app:
  theme is "dark"

ui:
  theme is "minimal"

page "home":
  title is "Hello"
'''
    manifest = build_manifest(lower_ir_program(source), state={}, store=None)
    assert manifest["theme"]["setting"] == "dark"
    assert manifest["theme"]["current"] == "dark"
    assert manifest["theme"]["theme_name"] == "minimal"


def test_ui_theme_token_override_precedence_and_determinism() -> None:
    source = '''
ui:
  theme is "corporate"
  spacing_scale is 1.5
  border_radius is 8

page "home":
  title is "Hello"
'''
    first = build_manifest(lower_ir_program(source), state={}, store=None)
    second = build_manifest(lower_ir_program(source), state={}, store=None)
    assert first["theme"]["tokens"]["spacing_scale"] == 1.5
    assert first["theme"]["tokens"]["border_radius"] == 8
    assert first["theme"] == second["theme"]
    assert _hash_theme(first["theme"]) == _hash_theme(second["theme"])


def test_ui_theme_token_rejects_invalid_color() -> None:
    source = '''
ui:
  primary_color is "blue"

page "home":
  title is "Hello"
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "primary_color" in str(exc.value)
    assert "hex color value" in str(exc.value)


def test_ui_theme_rejects_unknown_token_name() -> None:
    source = '''
ui:
  primary_colour is "#007AFF"

page "home":
  title is "Hello"
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "Unknown ui field 'primary_colour'" in str(exc.value)

