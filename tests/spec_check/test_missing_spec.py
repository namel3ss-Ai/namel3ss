from __future__ import annotations

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.parser.core import parse
from namel3ss.spec_check.extract import extract_declared_spec


def test_missing_spec_raises() -> None:
    source = 'flow "demo":\n  return "ok"\n'
    program = parse(source, require_spec=False)
    with pytest.raises(Namel3ssError) as excinfo:
        extract_declared_spec(program)
    message = str(excinfo.value)
    assert "Spec declaration is missing" in message
    assert 'spec is "1.0"' in message
