from __future__ import annotations

from namel3ss.ui.manifest import build_manifest
from namel3ss.validation import ValidationMode
from tests.conftest import lower_ir_program


def _warning_codes(warnings: list) -> list[str]:
    return sorted(str(getattr(warning, "code", "")) for warning in warnings)


def test_upload_warning_when_capability_enabled_without_control() -> None:
    source = '''
spec is "1.0"

capabilities:
  uploads

flow "demo":
  return "ok"

page "home":
  title is "Home"
'''.lstrip()
    warnings: list = []
    build_manifest(lower_ir_program(source), state={}, store=None, mode=ValidationMode.STATIC, warnings=warnings)
    assert "upload.missing_control" in _warning_codes(warnings)


def test_upload_warning_when_declaration_is_unused() -> None:
    source = '''
spec is "1.0"

page "home":
  upload receipt
'''.lstrip()
    warnings: list = []
    build_manifest(lower_ir_program(source), state={}, store=None, mode=ValidationMode.STATIC, warnings=warnings)
    assert "upload.unused_declaration" in _warning_codes(warnings)


def test_upload_warning_not_emitted_when_flow_references_upload_state() -> None:
    source = '''
spec is "1.0"

flow "submit":
  let files is state.uploads.receipt
  return files

page "home":
  upload receipt
'''.lstrip()
    warnings: list = []
    build_manifest(lower_ir_program(source), state={}, store=None, mode=ValidationMode.STATIC, warnings=warnings)
    assert "upload.unused_declaration" not in _warning_codes(warnings)
