from __future__ import annotations

from tests.conftest import lower_ir_program


def _collect_elements(elements: list[dict]) -> list[dict]:
    out: list[dict] = []
    for element in elements:
        out.append(element)
        children = element.get("children")
        if isinstance(children, list):
            out.extend(_collect_elements(children))
    return out


def test_manifest_includes_theme_definition_and_component_styles() -> None:
    source = '''
capabilities:
  custom_theme

theme:
  preset: "clarity"
  brand_palette:
    brand_primary: "#6750A4"
    brand_accent: "#03DAC6"
  tokens:
    color.primary: color.brand_primary.600

flow "demo":
  return "ok"

page "home":
  card:
    variant is "elevated"
    style_hooks:
      background: color.primary
    text is "Welcome"
  button "Continue":
    variant is "primary"
    style_hooks:
      background: color.primary
      text: color.on_primary
    calls flow "demo"
'''
    program = lower_ir_program(source)
    from namel3ss.ui.manifest import build_manifest

    manifest_one = build_manifest(program, state={}, store=None)
    manifest_two = build_manifest(program, state={}, store=None)

    assert manifest_one == manifest_two
    theme = manifest_one["theme"]
    assert theme["preference"]["storage_key"] == "namel3ss_theme"
    assert theme["definition"]["brand_palette"]["brand_primary"] == "#6750A4"
    assert theme["tokens"]["color.primary"].startswith("#")
    elements = _collect_elements(manifest_one["pages"][0]["elements"])
    card = next(item for item in elements if item.get("type") == "card")
    button = next(item for item in elements if item.get("type") == "button")
    assert card.get("variant") == "elevated"
    assert card.get("style", {}).get("tokens", {}).get("background") == "color.primary"
    assert button.get("variant") == "primary"
    assert button.get("style", {}).get("tokens", {}).get("text") == "color.on_primary"

