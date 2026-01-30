from __future__ import annotations

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir.model.tools import ToolField
from namel3ss.runtime.tools.schema_validate import validate_tool_fields


def test_tool_output_validation_is_deterministic() -> None:
    fields = [ToolField(name="message", type_name="text", required=True, line=1, column=1)]
    payload = {"message": 123}

    with pytest.raises(Namel3ssError) as exc_first:
        validate_tool_fields(
            fields=fields,
            payload=payload,
            tool_name="demo",
            phase="output",
            line=None,
            column=None,
        )

    with pytest.raises(Namel3ssError) as exc_second:
        validate_tool_fields(
            fields=fields,
            payload=payload,
            tool_name="demo",
            phase="output",
            line=None,
            column=None,
        )

    assert str(exc_first.value) == str(exc_second.value)
    assert "message" in str(exc_first.value)
