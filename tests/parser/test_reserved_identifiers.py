from __future__ import annotations

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.parser.core import parse


def test_reserved_keyword_as_identifier_has_guidance():
    source = 'spec is "1.0"\n\nflow "demo":\n  let title is "x"\n'
    with pytest.raises(Namel3ssError) as excinfo:
        parse(source)
    err = excinfo.value
    # Error classification is explicit for reserved identifiers.
    assert isinstance(err.details, dict)
    assert err.details.get("error_id") == "parse.reserved_identifier"
    assert err.details.get("keyword") == "title"
    message = str(err).lower()
    assert "reserved" in message
    assert "title" in message
    assert "escaped form" in message
    assert "`title`" in str(err)
