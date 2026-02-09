from namel3ss.determinism import canonical_json_dumps
from namel3ss.ui.manifest import build_manifest
from tests.conftest import lower_ir_program


SOURCE = '''spec is "1.0"

capabilities:
  ui_navigation
  app_permissions

permissions:
  navigation:
    change_page: allowed
  uploads:
    write: denied
    read: denied
  ai:
    tools: denied
    call: denied
  ui_state:
    persistent_write: denied

page "Chat":
  button "Open settings":
    navigate_to "Settings"

page "Settings":
  text is "Ready"
'''


def test_permissions_manifest_determinism() -> None:
    program = lower_ir_program(SOURCE)
    first = build_manifest(program, state={}, store=None)
    second = build_manifest(program, state={}, store=None)
    assert canonical_json_dumps(first, pretty=False) == canonical_json_dumps(second, pretty=False)
    permission_keys = list((first.get("permissions") or {}).keys())
    assert permission_keys == sorted(permission_keys)
