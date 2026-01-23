from __future__ import annotations

import re

from namel3ss.ui.manifest import build_manifest
from namel3ss.validation import ValidationMode
from tests.conftest import lower_ir_program


MIXED_COMPONENT_SOURCE = '''spec is "1.0"

record "Order":
  name text

page "orders":
  table is "Order"

page "orders list":
  list is "Order":
    item:
      primary is name
'''

INCONSISTENT_COLUMNS_SOURCE = '''spec is "1.0"

record "Order":
  name text
  status text
  total number

page "orders":
  table is "Order":
    columns:
      include name
      include status

page "orders total":
  table is "Order":
    columns:
      include name
      include total
'''

CHART_PAIRING_SOURCE = '''spec is "1.0"

record "Order":
  name text
  total number

page "table view":
  table is "Order"
  chart is "Order":
    type is bar
    x is name
    y is total

page "list view":
  list is "Order":
    item:
      primary is name
  chart is "Order":
    type is bar
    x is name
    y is total
'''

CONSISTENT_SOURCE = '''spec is "1.0"

record "Order":
  name text
  total number

page "a":
  table is "Order":
    columns:
      include name
      include total

page "b":
  table is "Order":
    columns:
      include name
      include total
'''

ORDERING_SOURCE = '''spec is "1.0"

record "Order":
  name text
  status text
  total number

record "Invoice":
  name text
  amount number
  status text

page "alpha":
  table is "Order"
  chart is "Order":
    type is bar
    x is name
    y is total
  table is "Invoice":
    columns:
      include name
      include amount

page "beta":
  list is "Order":
    item:
      primary is name
  chart is "Order":
    type is bar
    x is name
    y is total
  table is "Invoice":
    columns:
      include name
      include status
'''


_RECORD_RE = re.compile(r'Record "([^"]+)"')


def _consistency_warnings(warnings: list) -> list:
    return [warning for warning in warnings if getattr(warning, "code", "").startswith("consistency.")]


def _warning_record_name(warning) -> str:
    message = getattr(warning, "message", "") or ""
    match = _RECORD_RE.search(message)
    return match.group(1) if match else ""


def _warning_sort_key(warning) -> tuple[str, str, str, int, int]:
    return (
        warning.code,
        _warning_record_name(warning),
        warning.path or "",
        warning.line or 0,
        warning.column or 0,
    )


def test_consistency_mixed_component_types() -> None:
    program = lower_ir_program(MIXED_COMPONENT_SOURCE)
    warnings: list = []
    build_manifest(program, state={}, mode=ValidationMode.STATIC, warnings=warnings)
    codes = {warning.code for warning in _consistency_warnings(warnings)}
    assert "consistency.record_component_type" in codes


def test_consistency_inconsistent_columns() -> None:
    program = lower_ir_program(INCONSISTENT_COLUMNS_SOURCE)
    warnings: list = []
    build_manifest(program, state={}, mode=ValidationMode.STATIC, warnings=warnings)
    codes = {warning.code for warning in _consistency_warnings(warnings)}
    assert "consistency.record_configuration" in codes


def test_consistency_chart_pairing() -> None:
    program = lower_ir_program(CHART_PAIRING_SOURCE)
    warnings: list = []
    build_manifest(program, state={}, mode=ValidationMode.STATIC, warnings=warnings)
    codes = {warning.code for warning in _consistency_warnings(warnings)}
    assert "consistency.chart_pairing" in codes


def test_consistency_order_is_deterministic() -> None:
    program = lower_ir_program(ORDERING_SOURCE)
    warnings_first: list = []
    warnings_second: list = []
    build_manifest(program, state={}, mode=ValidationMode.STATIC, warnings=warnings_first)
    build_manifest(program, state={}, mode=ValidationMode.STATIC, warnings=warnings_second)
    first = _consistency_warnings(warnings_first)
    second = _consistency_warnings(warnings_second)
    assert [warning.to_dict() for warning in first] == [warning.to_dict() for warning in second]
    ordered = sorted(first, key=_warning_sort_key)
    assert [warning.to_dict() for warning in first] == [warning.to_dict() for warning in ordered]


def test_consistency_rules_skip_consistent_apps() -> None:
    program = lower_ir_program(CONSISTENT_SOURCE)
    warnings: list = []
    build_manifest(program, state={}, mode=ValidationMode.STATIC, warnings=warnings)
    assert not _consistency_warnings(warnings)
