from __future__ import annotations

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.icons.registry import icon_names, validate_icon_name, normalize_icon_name


def test_icon_names_are_deterministic_and_unique():
    names = icon_names()
    assert names == tuple(sorted(names))
    assert len(names) == len(set(names))
    assert names, "Icon registry is empty"


def test_unknown_icon_suggests_fix():
    with pytest.raises(Namel3ssError) as excinfo:
        validate_icon_name("ad", line=1, column=1)
    message = str(excinfo.value).lower()
    assert "unknown icon" in message
    assert "did you mean" in message or "n3 icons" in message


def test_normalization_is_lower_snake_case():
    assert normalize_icon_name("Add-Link ") == "add_link"
