from __future__ import annotations

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.ui.manifest import build_manifest
from tests.conftest import lower_ir_program


def _find_by_type(elements: list[dict], target: str) -> dict:
    for element in elements:
        if element.get("type") == target:
            return element
    raise AssertionError(f"Missing element type: {target}")


def test_responsive_layout_manifest_includes_breakpoints_and_columns() -> None:
    source = '''
capabilities:
  responsive_design
  custom_theme

theme:
  tokens:
    font_size.base: [13, 14, 16, 18]
    spacing.small: [3, 4, 6, 8]

responsive:
  breakpoints:
    mobile: 0
    tablet: 640
    desktop: 1024

page "home":
  section "Overview" columns: [12, 6, 4]:
    grid:
      columns: [12, 6, 4]
      loading variant: spinner when state.busy
      snackbar message: "Saved" duration: 2000
      icon name: "info" role: "decorative" size: "medium"
      lightbox images: ["hero.png", "promo.png"] startIndex: 1
'''
    program = lower_ir_program(source)
    manifest = build_manifest(program, state={"busy": True}, store=None)

    responsive = manifest["ui"]["responsive"]
    assert responsive["enabled"] is True
    assert [entry["name"] for entry in responsive["breakpoints"]] == ["mobile", "tablet", "desktop"]
    assert responsive["token_scales"]["font_size.base"] == [13, 14, 16, 18]

    section = _find_by_type(manifest["pages"][0]["elements"], "section")
    assert section["columns"] == [12, 6, 4]
    grid = _find_by_type(section["children"], "grid")
    assert grid["columns"] == [12, 6, 4]
    assert _find_by_type(grid["children"], "loading")["variant"] == "spinner"
    assert _find_by_type(grid["children"], "snackbar")["duration_ms"] == 2000
    assert _find_by_type(grid["children"], "icon")["name"] == "info"
    assert _find_by_type(grid["children"], "lightbox")["start_index"] == 1


def test_responsive_columns_fallback_to_static_without_capability() -> None:
    source = '''
page "home":
  section "Overview" columns: [12, 6, 4]:
    text is "Hello"
'''
    program = lower_ir_program(source)
    manifest = build_manifest(program, state={}, store=None)

    section = _find_by_type(manifest["pages"][0]["elements"], "section")
    assert section["columns"] == [12]
    assert "responsive" not in manifest["ui"]


def test_responsive_token_scale_requires_default_plus_breakpoints() -> None:
    source = '''
capabilities:
  responsive_design
  custom_theme

theme:
  tokens:
    font_size.base: [14, 16]

responsive:
  breakpoints:
    mobile: 0
    desktop: 1024

page "home":
  text is "Hello"
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "default + 2 breakpoints" in exc.value.message


def test_responsive_columns_pad_with_first_span_value() -> None:
    source = '''
capabilities:
  responsive_design

responsive:
  breakpoints:
    mobile: 0
    tablet: 640
    desktop: 1024

page "home":
  section "Overview" columns: [10, 6]:
    text is "Hello"
'''
    program = lower_ir_program(source)
    manifest = build_manifest(program, state={}, store=None)
    section = _find_by_type(manifest["pages"][0]["elements"], "section")
    assert section["columns"] == [10, 6, 10]
