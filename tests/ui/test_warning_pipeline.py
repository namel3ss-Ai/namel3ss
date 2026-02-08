from __future__ import annotations

from namel3ss.ui.manifest import build_manifest
from namel3ss.ui.manifest.warning_pipeline import warning_pipeline_names
from namel3ss.validation import ValidationMode
from tests.conftest import lower_ir_program


PIPELINE_SOURCE = '''spec is "1.0"

capabilities:
  uploads

record "Order":
  name text
  total number

flow "launch":
  return "ok"

page "home":
  table is "Order"
  list is "Order":
    item:
      primary is name
  story "Signals":
    step "Needs icon":
      tone is "critical"
  section:
    text is "Unlabeled"
  button "More details about the report status and metrics":
    calls flow "launch"
'''

GOOD_SOURCE = '''spec is "1.0"

record "Order":
  name text
  total number

flow "launch":
  return "ok"

page "home":
  title is "Dashboard"
  text is "Overview of orders."
  section "Orders":
    table is "Order":
      empty_state: hidden
'''

_UI_PREFIXES = ("layout.", "upload.", "visibility.", "diagnostics.", "copy.", "story.", "icon.", "consistency.")
_PIPELINE_INDEX = {
    "layout": 0,
    "upload": 1,
    "visibility": 2,
    "diagnostics": 3,
    "copy": 4,
    "story": 5,
    "icon": 5,
    "consistency": 6,
}


def _ui_warnings(warnings: list) -> list:
    return [warning for warning in warnings if str(getattr(warning, "code", "")).startswith(_UI_PREFIXES)]


def test_warning_pipeline_names_are_fixed() -> None:
    assert warning_pipeline_names() == ("layout", "upload", "visibility", "diagnostics", "copy", "story_icon", "consistency")


def test_warning_pipeline_order_is_deterministic() -> None:
    program = lower_ir_program(PIPELINE_SOURCE)
    first_warnings: list = []
    second_warnings: list = []

    build_manifest(program, state={}, mode=ValidationMode.STATIC, warnings=first_warnings)
    build_manifest(program, state={}, mode=ValidationMode.STATIC, warnings=second_warnings)

    first_ui = _ui_warnings(first_warnings)
    second_ui = _ui_warnings(second_warnings)

    assert [warning.to_dict() for warning in first_ui] == [warning.to_dict() for warning in second_ui]
    assert first_ui

    steps = [_PIPELINE_INDEX[warning.code.split(".", 1)[0]] for warning in first_ui]
    assert steps == sorted(steps)

    required_codes = {
        "layout.mixed_record_representation",
        "upload.missing_control",
        "visibility.missing_empty_state_guard",
        "copy.missing_page_title",
        "story.tone_missing_icon",
    }
    assert required_codes.issubset({warning.code for warning in first_ui})

    for warning in first_ui:
        payload = warning.to_dict()
        for key in ("code", "message", "fix", "path", "line", "column", "category"):
            assert key in payload


def test_warning_pipeline_emits_diagnostics_warnings() -> None:
    program = lower_ir_program(
        '''flow "launch":
  return "ok"

page "home":
  button "Debug action" debug_only is true:
    calls flow "launch"
'''
    )
    warnings: list = []
    build_manifest(program, state={}, mode=ValidationMode.STATIC, warnings=warnings)
    codes = [warning.code for warning in _ui_warnings(warnings)]
    assert "diagnostics.misplaced_debug_content" in codes


def test_warning_pipeline_skips_clean_pages() -> None:
    program = lower_ir_program(GOOD_SOURCE)
    warnings: list = []
    build_manifest(program, state={}, mode=ValidationMode.STATIC, warnings=warnings)
    assert not _ui_warnings(warnings)
