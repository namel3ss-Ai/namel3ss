from __future__ import annotations

import pytest

from namel3ss import contract as build_contract
from namel3ss.errors.base import Namel3ssError


def test_validate_requires_flow() -> None:
    source = '''spec is "1.0"

record "Item":
  name text
'''
    contract_obj = build_contract(source)
    with pytest.raises(Namel3ssError) as excinfo:
        contract_obj.validate()
    message = str(excinfo.value)
    assert "No flows defined" in message
    assert "Add a flow block" in message
