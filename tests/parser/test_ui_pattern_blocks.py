import pytest

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.parser.core import parse


def test_ui_pattern_parses_and_use():
    source = '''spec is "1.0"

pattern "Notice":
  parameters:
    heading is text
    count is number optional
  title is param.heading

page "home":
  use pattern "Notice":
    heading is "Hello"
'''
    program = parse(source)
    assert len(program.ui_patterns) == 1
    pattern = program.ui_patterns[0]
    assert pattern.name == "Notice"
    assert [param.name for param in pattern.parameters] == ["heading", "count"]
    assert pattern.parameters[0].kind == "text"
    assert isinstance(pattern.items[0], ast.TitleItem)
    assert isinstance(pattern.items[0].value, ast.PatternParamRef)
    assert pattern.items[0].value.name == "heading"
    page = program.pages[0]
    use = page.items[0]
    assert isinstance(use, ast.UsePatternItem)
    assert use.pattern_name == "Notice"
    assert use.arguments[0].name == "heading"
    assert use.arguments[0].value == "Hello"


def test_ui_pattern_requires_entries():
    source = '''spec is "1.0"

pattern "Empty":
  parameters:
    heading is text
'''
    with pytest.raises(Namel3ssError) as exc:
        parse(source)
    assert "pattern has no entries" in str(exc.value).lower()


@pytest.mark.parametrize(
    "snippet",
    [
        'flow "demo":\n    return "ok"',
        'record "User":\n    name is text',
        'tool "Search":\n    kind is "http"',
    ],
)
def test_ui_pattern_rejects_forbidden_blocks(snippet: str):
    source = f'''spec is "1.0"

pattern "Bad":
  {snippet}
'''
    with pytest.raises(Namel3ssError) as exc:
        parse(source)
    assert "unexpected item" in str(exc.value).lower()
