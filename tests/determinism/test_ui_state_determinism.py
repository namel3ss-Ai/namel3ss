from namel3ss.determinism import canonical_json_dumps
from namel3ss.ui.manifest import build_manifest
from tests.conftest import lower_ir_program


SOURCE = """spec is "1.0"

capabilities:
  ui_state

ui_state:
  session:
    current_page is text
  persistent:
    theme is text

page "Chat":
  text is "Chat page"

page "Settings":
  text is "Settings page"
"""


def test_ui_state_manifest_determinism() -> None:
    program = lower_ir_program(SOURCE)
    state = {"ui": {"current_page": "Settings", "theme": "dark"}}
    first = build_manifest(program, state=state, store=None)
    second = build_manifest(program, state=state, store=None)
    assert canonical_json_dumps(first, pretty=False) == canonical_json_dumps(second, pretty=False)
