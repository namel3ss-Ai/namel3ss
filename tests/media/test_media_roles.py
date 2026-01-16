from __future__ import annotations

import pytest

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from tests.conftest import lower_ir_program, parse_program


def test_page_image_role_parses() -> None:
    source = '''page "home":
  image is "hero":
    role is "illustration"
'''
    program = parse_program(source)
    image = program.pages[0].items[0]
    assert isinstance(image, ast.ImageItem)
    assert image.role == "illustration"


def test_story_image_role_lowers() -> None:
    source = '''page "home":
  story "Flow":
    step "Start":
      image is "hero":
        role is "iconic"
'''
    program = lower_ir_program(source)
    story = program.pages[0].items[0]
    assert story.steps[0].image_role == "iconic"


def test_invalid_image_role_rejected() -> None:
    source = '''page "home":
  image is "hero":
    role is "loud"
'''
    with pytest.raises(Namel3ssError) as excinfo:
        lower_ir_program(source)
    assert "role" in str(excinfo.value).lower()
