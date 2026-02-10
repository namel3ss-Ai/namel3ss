from __future__ import annotations

from namel3ss.ui.manifest import build_manifest
from tests.conftest import lower_ir_program


def test_theme_manifest_contains_phase4_fields_and_is_deterministic() -> None:
    source = 'page "home":\n  title is "Hello"\n'
    program = lower_ir_program(source)

    first = build_manifest(program, state={}, store=None)
    second = build_manifest(program, state={}, store=None)

    assert first == second
    theme = first["theme"]
    assert theme["base_theme"] == "default"
    assert theme["config"]["base_theme"] == "default"
    assert isinstance(theme["token_schema"], dict)
    assert theme["themes_available"] == ["default", "dark", "high_contrast"]


def test_theme_manifest_preserves_existing_visual_theme_name_without_explicit_theme_config() -> None:
    source = 'ui:\n  theme is "modern"\n\npage "home":\n  title is "Hello"\n'
    manifest = build_manifest(lower_ir_program(source), state={}, store=None)
    assert manifest["theme"]["theme_name"] == "modern"


def test_theme_manifest_applies_explicit_theme_config_override() -> None:
    source = 'page "home":\n  title is "Hello"\n'
    program = lower_ir_program(source)
    setattr(
        program,
        "ui_theme_config",
        {
            "base_theme": "high_contrast",
            "overrides": {
                "primary_color": "#FFAA00",
                "spacing_scale": 1.2,
            },
        },
    )

    manifest = build_manifest(program, state={}, store=None)
    theme = manifest["theme"]
    assert theme["base_theme"] == "high_contrast"
    assert theme["theme_name"] == "high_contrast"
    assert theme["tokens"]["primary_color"] == "#FFAA00"
    assert theme["tokens"]["spacing_scale"] == 1.2


def test_theme_manifest_includes_runtime_ui_theme_tokens_when_capability_is_enabled() -> None:
    source = 'spec is "1.0"\n\ncapabilities:\n  ui_theme\n\npage "theme":\n  include theme_settings_page\n'
    program = lower_ir_program(source)
    manifest = build_manifest(
        program,
        state={"ui": {"settings": {"size": "compact", "radius": "sm", "density": "tight", "font": "lg", "color_scheme": "dark"}}},
        store=None,
    )
    theme = manifest["theme"]
    assert theme["size"] == "compact"
    assert theme["radius"] == "sm"
    assert theme["density"] == "tight"
    assert theme["font"] == "lg"
    assert theme["color_scheme"] == "dark"
