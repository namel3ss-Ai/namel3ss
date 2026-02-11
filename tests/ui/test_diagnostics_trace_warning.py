from __future__ import annotations

from namel3ss.ir.validation.includes_validation import DIAGNOSTICS_TRACE_WARNING_MESSAGE
from namel3ss.ui.manifest import build_manifest
from namel3ss.validation import ValidationMode
from tests.conftest import lower_ir_program


SOURCE_MISSING_TRACE_CAPABILITY = '''
spec is "1.0"

capabilities:
  uploads

contract flow "set_semantic_weight":
  input:
    weight is number
  output:
    ok is text

flow "set_semantic_weight":
  let _value is set_semantic_weight(input.weight)
  return "ok"

page "home":
  text is "Hello"
'''.lstrip()


SOURCE_WITH_TRACE_CAPABILITY = '''
spec is "1.0"

capabilities:
  uploads
  diagnostics.trace

contract flow "set_semantic_weight":
  input:
    weight is number
  output:
    ok is text

flow "set_semantic_weight":
  let _value is set_semantic_weight(input.weight)
  return "ok"

page "home":
  text is "Hello"
'''.lstrip()


def test_manifest_emits_diagnostics_trace_warning_when_capability_missing() -> None:
    warnings: list = []
    program = lower_ir_program(SOURCE_MISSING_TRACE_CAPABILITY)
    build_manifest(program, state={}, mode=ValidationMode.STATIC, warnings=warnings)

    warning = next(entry for entry in warnings if getattr(entry, "code", "") == "diagnostics.trace.disabled")
    assert warning.message == DIAGNOSTICS_TRACE_WARNING_MESSAGE


def test_manifest_skips_diagnostics_trace_warning_when_capability_present() -> None:
    warnings: list = []
    program = lower_ir_program(SOURCE_WITH_TRACE_CAPABILITY)
    build_manifest(program, state={}, mode=ValidationMode.STATIC, warnings=warnings)

    codes = [getattr(entry, "code", "") for entry in warnings]
    assert "diagnostics.trace.disabled" not in codes

