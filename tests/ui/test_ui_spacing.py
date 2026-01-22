from namel3ss.ui.manifest import build_manifest
from tests.conftest import lower_ir_program


BASE_BODY = '''record "User":
  name text
  email text
  age number

flow "send":
  return "ok"

page "home":
  compose stats:
    section "Overview":
      row:
        column:
          card "Summary":
            text is "Hello"
  card_group:
    card "Card":
      text is "Done"
  tabs:
    tab "First":
      text is "One"
    tab "Second":
      text is "Two"
  modal "Confirm":
    text is "Sure"
  drawer "Details":
    text is "More"
  form is "User"
  table is "User"
  list is "User":
    item:
      primary is name
  chart is "User":
    type is bar
    x is name
    y is age
  chat:
    messages from is state.messages
    composer calls flow "send"
'''


def _source_with_density(density: str | None) -> str:
    ui_block = f'ui:\n  density is "{density}"\n\n' if density else ""
    return f'spec is "1.0"\n\n{ui_block}{BASE_BODY}'


def _flatten(elements: list[dict]) -> list[dict]:
    items: list[dict] = []
    for element in elements:
        items.append(element)
        children = element.get("children")
        if isinstance(children, list):
            items.extend(_flatten(children))
    return items


def _by_type(manifest: dict) -> dict[str, dict]:
    elements = manifest.get("pages", [{}])[0].get("elements", [])
    return {element["type"]: element for element in _flatten(elements) if isinstance(element, dict) and "type" in element}


def test_spacing_applies_to_layout_and_components():
    program = lower_ir_program(_source_with_density("compact"))
    manifest = build_manifest(program, state={})
    by_type = _by_type(manifest)
    required = [
        "compose",
        "section",
        "row",
        "column",
        "card_group",
        "card",
        "tabs",
        "tab",
        "modal",
        "drawer",
        "form",
        "table",
        "list",
        "chart",
        "chat",
        "messages",
        "composer",
    ]
    for element_type in required:
        assert "spacing" in by_type[element_type]


def test_spacing_differs_by_density():
    compact = build_manifest(lower_ir_program(_source_with_density("compact")), state={})
    spacious = build_manifest(lower_ir_program(_source_with_density("spacious")), state={})
    compact_section = _by_type(compact)["section"]["spacing"]
    spacious_section = _by_type(spacious)["section"]["spacing"]
    assert compact_section != spacious_section


def test_spacing_is_deterministic_for_same_density():
    program = lower_ir_program(_source_with_density("comfortable"))
    first = build_manifest(program, state={})
    second = build_manifest(program, state={})
    assert first == second


def test_default_density_matches_comfortable():
    default_manifest = build_manifest(lower_ir_program(_source_with_density(None)), state={})
    comfortable_manifest = build_manifest(lower_ir_program(_source_with_density("comfortable")), state={})
    assert default_manifest["ui"]["settings"]["density"] == "comfortable"
    default_spacing = _by_type(default_manifest)["section"]["spacing"]
    comfortable_spacing = _by_type(comfortable_manifest)["section"]["spacing"]
    assert default_spacing == comfortable_spacing
