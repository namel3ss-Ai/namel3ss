from namel3ss.studio.api import get_actions_payload, get_ui_payload
from namel3ss.studio.session import SessionState
from namel3ss.ui.manifest import build_manifest
from namel3ss.validation import ValidationMode
from tests.conftest import lower_ir_program


LONG_TEXT = "A" * 201

POOR_COPY_SOURCE = f'''spec is "1.0"

record "Order":
  name text
  status text
  total number

flow "launch":
  return "ok"

page "home":
  table is "Order"
  text is "{LONG_TEXT}"
  section:
    text is "Unlabeled section"
  section "Details":
    card:
      text is "Card text"
  section "Details":
    text is "Duplicate label"
  button "More details about the report status and metrics":
    calls flow "launch"
  link "Settings" to page "Settings"

page "Settings":
  title is "Settings"
  text is "Preferences"
'''

GOOD_COPY_SOURCE = '''spec is "1.0"

record "Order":
  name text
  total number

flow "launch":
  return "ok"

page "home":
  title is "Dashboard"
  text is "Overview of orders."
  section "Summary":
    card "Orders":
      text is "All set."
      button "View orders":
        calls flow "launch"
  table is "Order"

page "Settings":
  title is "Settings"
  text is "Preferences."
'''


def _copy_warnings(warnings: list) -> list:
    return [warning for warning in warnings if getattr(warning, "code", "").startswith("copy.")]


def _warning_sort_key(warning) -> tuple[str, str, int, int]:
    return (
        warning.code,
        warning.path or "",
        warning.line or 0,
        warning.column or 0,
    )


def test_copy_rules_emit_expected_warnings() -> None:
    program = lower_ir_program(POOR_COPY_SOURCE)
    warnings: list = []
    build_manifest(program, state={}, mode=ValidationMode.STATIC, warnings=warnings)
    codes = {warning.code for warning in _copy_warnings(warnings)}
    expected = {
        "copy.action_label",
        "copy.duplicate_container_label",
        "copy.missing_intro_text",
        "copy.missing_page_title",
        "copy.text_too_long",
        "copy.unlabeled_container",
    }
    assert expected.issubset(codes)


def test_copy_rules_order_is_deterministic() -> None:
    program = lower_ir_program(POOR_COPY_SOURCE)
    warnings_first: list = []
    warnings_second: list = []
    build_manifest(program, state={}, mode=ValidationMode.STATIC, warnings=warnings_first)
    build_manifest(program, state={}, mode=ValidationMode.STATIC, warnings=warnings_second)
    copy_first = _copy_warnings(warnings_first)
    copy_second = _copy_warnings(warnings_second)
    assert [warning.to_dict() for warning in copy_first] == [warning.to_dict() for warning in copy_second]
    ordered = sorted(copy_first, key=_warning_sort_key)
    assert [warning.to_dict() for warning in copy_first] == [warning.to_dict() for warning in ordered]


def test_copy_rules_skip_clean_pages() -> None:
    program = lower_ir_program(GOOD_COPY_SOURCE)
    warnings: list = []
    build_manifest(program, state={}, mode=ValidationMode.STATIC, warnings=warnings)
    assert not _copy_warnings(warnings)


def test_copy_warnings_surface_in_studio_payloads(tmp_path) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text(POOR_COPY_SOURCE, encoding="utf-8")
    session = SessionState()
    manifest = get_ui_payload(POOR_COPY_SOURCE, session, app_path.as_posix())
    manifest_codes = {warning["code"] for warning in manifest.get("warnings", [])}
    assert "copy.missing_page_title" in manifest_codes
    actions_payload = get_actions_payload(POOR_COPY_SOURCE, app_path.as_posix())
    action_codes = {warning["code"] for warning in actions_payload.get("warnings", [])}
    assert "copy.missing_page_title" in action_codes
