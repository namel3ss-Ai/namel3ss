from namel3ss.determinism import canonical_json_dumps
from namel3ss.ui.manifest import build_manifest
from tests.conftest import lower_ir_program

SOURCE = """spec is "1.0"

capabilities:
  ui_navigation

nav_sidebar:
  item "Chat" goes_to "Chat"
  item "Settings" goes_to "Settings"

page "Chat":
  button "Settings":
    navigate_to "Settings"

page "Settings":
  button "Back":
    go_back
"""


def test_ui_navigation_manifest_determinism() -> None:
    program = lower_ir_program(SOURCE)
    first = build_manifest(program, state={}, store=None)
    second = build_manifest(program, state={}, store=None)
    assert canonical_json_dumps(first, pretty=False) == canonical_json_dumps(second, pretty=False)
