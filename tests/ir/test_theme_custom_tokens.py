from __future__ import annotations

import pytest

from namel3ss.errors.base import Namel3ssError
from tests.conftest import lower_ir_program


def _walk_items(items: list[object]) -> list[object]:
    all_items: list[object] = []
    for item in items:
        all_items.append(item)
        children = getattr(item, "children", None)
        if isinstance(children, list):
            all_items.extend(_walk_items(children))
    return all_items


def test_custom_theme_requires_capability() -> None:
    source = '''
theme:
  brand_palette:
    brand_primary: "#6200EE"
page "home":
  title is "Hello"
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "custom_theme" in str(exc.value)


def test_theme_tokens_variants_and_style_hooks_lower() -> None:
    source = '''
capabilities:
  custom_theme

theme:
  preset: "clarity"
  brand_palette:
    brand_primary: "#6200EE"
    functional_success: "#2E7D32"
  tokens:
    color.primary: color.brand_primary.600
    color.success: color.functional_success.500
  harmonize: true
  density: "compact"

flow "demo":
  return "ok"

page "home":
  card:
    variant is "outlined"
    style_hooks:
      background: color.primary
      border: color.success
    text is "Hello"
  button "Save":
    variant is "success"
    style_hooks:
      background: color.primary
      text: color.on_primary
    calls flow "demo"
'''
    program = lower_ir_program(source)
    assert program.ui_settings["density"] == "compact"
    assert program.theme_tokens["color.primary"].startswith("#")
    assert program.theme_tokens["color.success"].startswith("#")
    page = program.pages[0]
    items = _walk_items(page.items)
    card = next(item for item in items if type(item).__name__ == "CardItem")
    button = next(item for item in items if type(item).__name__ == "ButtonItem")
    assert getattr(card, "variant", None) == "outlined"
    assert getattr(button, "variant", None) == "success"
    assert getattr(card, "style_hooks", {}).get("background") == "color.primary"
    assert getattr(button, "style_hooks", {}).get("text") == "color.on_primary"


def test_invalid_variant_rejected() -> None:
    source = '''
flow "demo":
  return "ok"

page "home":
  button "Save":
    variant is "tertiary"
    calls flow "demo"
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "Unknown variant" in str(exc.value)


def test_button_plain_variant_is_allowed() -> None:
    source = '''
flow "demo":
  return "ok"

page "home":
  button "New project":
    variant is "plain"
    calls flow "demo"
'''
    program = lower_ir_program(source)
    page = program.pages[0]
    button = next(item for item in _walk_items(page.items) if type(item).__name__ == "ButtonItem")
    assert getattr(button, "variant", None) == "plain"


def test_style_hooks_require_known_tokens() -> None:
    source = '''
capabilities:
  custom_theme

theme:
  brand_palette:
    brand_primary: "#6200EE"

flow "demo":
  return "ok"

page "home":
  card:
    style_hooks:
      background: color.unknown
    text is "Hello"
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "unknown token" in str(exc.value).lower()


def test_theme_supports_responsive_token_scales() -> None:
    source = '''
capabilities:
  custom_theme

theme:
  tokens:
    font_size.base: [14, 16, 18]
    spacing.small: [4, 6, 8]

page "home":
  title is "Hello"
'''
    program = lower_ir_program(source)
    scales = getattr(program, "responsive_theme_tokens", {})
    assert scales["font_size.base"] == (14, 16, 18)
    assert scales["spacing.small"] == (4, 6, 8)
