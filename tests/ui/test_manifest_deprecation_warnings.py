from __future__ import annotations

from namel3ss.config.loader import load_config
from namel3ss.validation import ValidationWarning
from namel3ss.validation_entrypoint import build_static_manifest
from tests.conftest import lower_ir_program


def test_manifest_builder_appends_capability_deprecation_warnings(tmp_path) -> None:
    source = """spec is "1.0"

capabilities:
  custom_ui
  ui_theme

page "Home":
  text is "Hello"
"""
    program = lower_ir_program(source)
    warnings: list[ValidationWarning] = []
    manifest = build_static_manifest(
        program,
        config=load_config(root=tmp_path),
        state={},
        store=None,
        warnings=warnings,
    )
    assert manifest["pages"]
    deprecation_codes = [warning.code for warning in warnings if warning.code.startswith("deprecation.")]
    assert deprecation_codes == [
        "deprecation.capability.custom_ui",
        "deprecation.capability.ui_theme",
    ]
