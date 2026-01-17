from namel3ss.ui.manifest import build_manifest
from tests.conftest import lower_ir_program


SOURCE = '''page "home":
  link "Settings" to page "Settings"

page "Settings":
  title is "Settings"
'''


def test_link_manifest_creates_open_page_action():
    program = lower_ir_program(SOURCE)
    manifest = build_manifest(program, state={})
    page = manifest["pages"][0]
    link = next(el for el in page["elements"] if el["type"] == "link")
    action_id = link["action_id"]
    action = manifest["actions"][action_id]
    assert action["type"] == "open_page"
    assert action["target"] == "Settings"
    assert link["action"]["type"] == "open_page"
    assert link["action"]["target"] == "Settings"


def test_link_manifest_is_deterministic():
    program = lower_ir_program(SOURCE)
    first = build_manifest(program, state={})
    second = build_manifest(program, state={})
    assert first == second
