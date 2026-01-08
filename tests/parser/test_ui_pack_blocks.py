import pytest

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.parser.core import parse


def test_ui_pack_parses_and_use():
    source = '''spec is "1.0"

ui_pack "widgets":
  version is "1.2.3"
  fragment "summary":
    text is "Hello"

page "home":
  use ui_pack "widgets" fragment "summary"
'''
    program = parse(source)
    assert len(program.ui_packs) == 1
    pack = program.ui_packs[0]
    assert pack.name == "widgets"
    assert pack.version == "1.2.3"
    assert len(pack.fragments) == 1
    fragment = pack.fragments[0]
    assert fragment.name == "summary"
    assert isinstance(fragment.items[0], ast.TextItem)
    page = program.pages[0]
    use = page.items[0]
    assert isinstance(use, ast.UseUIPackItem)
    assert use.pack_name == "widgets"
    assert use.fragment_name == "summary"


def test_ui_pack_requires_version():
    source = '''spec is "1.0"

ui_pack "widgets":
  fragment "summary":
    text is "Hi"
'''
    with pytest.raises(Namel3ssError) as exc:
        parse(source)
    assert "requires a version" in str(exc.value).lower()


def test_ui_pack_rejects_duplicate_fragment_names():
    source = '''spec is "1.0"

ui_pack "widgets":
  version is "1"
  fragment "summary":
    text is "Hi"
  fragment "summary":
    text is "Again"
'''
    with pytest.raises(Namel3ssError) as exc:
        parse(source)
    assert "duplicated" in str(exc.value).lower()


@pytest.mark.parametrize("name", ["page", "flow"])
def test_ui_pack_rejects_keyword_names(name: str):
    source = f'''spec is "1.0"

ui_pack "{name}":
  version is "1"
  fragment "summary":
    text is "Hi"
'''
    with pytest.raises(Namel3ssError) as exc:
        parse(source)
    assert "reserved keyword" in str(exc.value).lower()


def test_ui_pack_rejects_keyword_fragment_names():
    source = '''spec is "1.0"

ui_pack "widgets":
  version is "1"
  fragment "page":
    text is "Hi"
'''
    with pytest.raises(Namel3ssError) as exc:
        parse(source)
    assert "reserved keyword" in str(exc.value).lower()
