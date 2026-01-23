from namel3ss.studio.api import get_actions_payload, get_ui_payload
from namel3ss.studio.session import SessionState
from namel3ss.ui.manifest import build_manifest
from namel3ss.validation import ValidationMode
from tests.conftest import lower_ir_program


BAD_SOURCE = '''spec is "1.0"

page "home":
  story "Signals":
    step "Missing icon":
      tone is "critical"
    step "Mismatch":
      tone is "caution"
      icon is check
    step "Neutral icon":
      icon is info
    step "Success A":
      tone is "success"
      icon is check
    step "Success B":
      tone is "success"
      icon is verified
  story "Overuse":
    step "One":
      tone is "informative"
      icon is info
    step "Two":
      tone is "informative"
      icon is info
    step "Three":
      tone is "informative"
      icon is info
'''

GOOD_SOURCE = '''spec is "1.0"

page "home":
  story "Onboarding":
    step "Start":
      tone is "informative"
      icon is info
    step "Finish":
      text is "Done"
  story "Plain":
    "One"
    "Two"
'''


def _story_icon_warnings(warnings: list) -> list:
    return [
        warning
        for warning in warnings
        if getattr(warning, "code", "").startswith(("story.", "icon."))
    ]


def _warning_sort_key(warning) -> tuple[str, str, int, int]:
    return (
        warning.code,
        warning.path or "",
        warning.line or 0,
        warning.column or 0,
    )


def test_story_icon_rules_emit_expected_warnings() -> None:
    program = lower_ir_program(BAD_SOURCE)
    warnings: list = []
    build_manifest(program, state={}, mode=ValidationMode.STATIC, warnings=warnings)
    codes = {warning.code for warning in _story_icon_warnings(warnings)}
    expected = {
        "story.icon_tone_mismatch",
        "story.tone_missing_icon",
        "story.tone_overuse",
        "icon.inconsistent_semantics",
        "icon.misuse",
        "icon.overuse",
    }
    assert expected.issubset(codes)


def test_story_icon_rules_order_is_deterministic() -> None:
    program = lower_ir_program(BAD_SOURCE)
    warnings_first: list = []
    warnings_second: list = []
    build_manifest(program, state={}, mode=ValidationMode.STATIC, warnings=warnings_first)
    build_manifest(program, state={}, mode=ValidationMode.STATIC, warnings=warnings_second)
    first = _story_icon_warnings(warnings_first)
    second = _story_icon_warnings(warnings_second)
    assert [warning.to_dict() for warning in first] == [warning.to_dict() for warning in second]
    ordered = sorted(first, key=_warning_sort_key)
    assert [warning.to_dict() for warning in first] == [warning.to_dict() for warning in ordered]


def test_story_icon_rules_skip_clean_pages() -> None:
    program = lower_ir_program(GOOD_SOURCE)
    warnings: list = []
    build_manifest(program, state={}, mode=ValidationMode.STATIC, warnings=warnings)
    assert not _story_icon_warnings(warnings)


def test_story_icon_warnings_surface_in_studio_payloads(tmp_path) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text(BAD_SOURCE, encoding="utf-8")
    session = SessionState()
    manifest = get_ui_payload(BAD_SOURCE, session, app_path.as_posix())
    manifest_codes = {warning["code"] for warning in manifest.get("warnings", [])}
    assert "story.tone_missing_icon" in manifest_codes
    assert "icon.misuse" in manifest_codes
    actions_payload = get_actions_payload(BAD_SOURCE, app_path.as_posix())
    action_codes = {warning["code"] for warning in actions_payload.get("warnings", [])}
    assert "story.tone_missing_icon" in action_codes
    assert "icon.misuse" in action_codes
