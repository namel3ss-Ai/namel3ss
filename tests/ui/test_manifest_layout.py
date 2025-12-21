from namel3ss.ui.manifest import build_manifest
from tests.conftest import lower_ir_program


SOURCE = '''flow "go":
  return "ok"

page "home":
  section "Top":
    row:
      column:
        card "First":
          button "Run":
            calls flow "go"
      column:
        text is "Other"
  divider
  image is "https://example.com/img.png"
'''


def test_manifest_includes_layout_elements_and_children():
    program = lower_ir_program(SOURCE)
    manifest = build_manifest(program)
    page = manifest["pages"][0]
    section = page["elements"][0]
    assert section["type"] == "section"
    assert section["label"] == "Top"
    row = section["children"][0]
    assert row["type"] == "row"
    column = row["children"][0]
    assert column["type"] == "column"
    card = column["children"][0]
    assert card["type"] == "card"
    button = card["children"][0]
    assert button["type"] == "button"
    divider = page["elements"][1]
    assert divider["type"] == "divider"
    image = page["elements"][2]
    assert image["type"] == "image"
    assert image["src"] == "https://example.com/img.png"
    assert isinstance(image["alt"], str)
    actions = manifest["actions"]
    assert "page.home.button.run" in actions
    assert actions["page.home.button.run"]["type"] == "call_flow"
