from namel3ss.ui.manifest import build_manifest
from namel3ss.validation import ValidationMode
from tests.conftest import lower_ir_program


POOR_LAYOUT_SOURCE = '''spec is "1.0"

record "Order":
  name text
  status text
  total number

flow "launch":
  return "ok"

page "home":
  text is "One"
  text is "Two"
  text is "Three"
  text is "Four"
  text is "Five"
  text is "Six"
  text is "Seven"
  text is "Eight"
  table is "Order"
  list is "Order":
    item:
      primary is name
  chart is "Order":
    type is bar
    x is name
    y is total
  card:
    button "A":
      calls flow "launch"
    button "B":
      calls flow "launch"
    button "C":
      calls flow "launch"
    button "D":
      calls flow "launch"
  section:
    row:
      column:
        card "Outer":
          row:
            column:
              card "Inner":
                text is "Deep"
  row:
    column:
      text is "Col1"
    column:
      text is "Col2"
    column:
      text is "Col3"
    column:
      text is "Col4"

page "orders":
  table is "Order":
    columns:
      include name
      include total

page "orders list":
  table is "Order":
    columns:
      include name
      include status
'''

GOOD_LAYOUT_SOURCE = '''spec is "1.0"

record "Order":
  name text
  total number

flow "launch":
  return "ok"

page "home":
  title is "Overview"
  section "Overview":
    card "Summary":
      text is "Ready"
      button "Run":
        calls flow "launch"
  section "Orders":
    table is "Order"
'''


def test_layout_rules_emit_expected_warnings() -> None:
    program = lower_ir_program(POOR_LAYOUT_SOURCE)
    warnings: list = []
    manifest = build_manifest(program, state={}, mode=ValidationMode.STATIC, warnings=warnings)
    assert manifest.get("pages")
    codes = {warning.code for warning in warnings}
    expected = {
        "layout.action_heavy",
        "layout.data_ungrouped",
        "layout.deep_nesting",
        "layout.flat_page_sprawl",
        "layout.grid_sprawl",
        "layout.inconsistent_columns",
        "layout.mixed_record_representation",
        "layout.unlabeled_container",
    }
    assert expected.issubset(codes)


def test_layout_rules_order_is_deterministic() -> None:
    program = lower_ir_program(POOR_LAYOUT_SOURCE)
    warnings_first: list = []
    warnings_second: list = []
    build_manifest(program, state={}, mode=ValidationMode.STATIC, warnings=warnings_first)
    build_manifest(program, state={}, mode=ValidationMode.STATIC, warnings=warnings_second)
    assert [warning.to_dict() for warning in warnings_first] == [warning.to_dict() for warning in warnings_second]


def test_layout_rules_skip_good_layouts() -> None:
    program = lower_ir_program(GOOD_LAYOUT_SOURCE)
    warnings: list = []
    build_manifest(program, state={}, mode=ValidationMode.STATIC, warnings=warnings)
    layout_warnings = [warning for warning in warnings if str(getattr(warning, "code", "")).startswith("layout.")]
    assert not layout_warnings
