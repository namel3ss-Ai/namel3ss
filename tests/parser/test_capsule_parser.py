import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.parser.core import parse


def test_capsule_parses_exports():
    source = (
        'spec is "1.0"\n\n'
        'capsule "inventory":\n'
        "  exports:\n"
        '    record "Product"\n'
        '    flow "calc_total"\n'
    )
    program = parse(source, allow_capsule=True)
    assert program.capsule is not None
    assert program.capsule.name == "inventory"
    exported = {(exp.kind, exp.name) for exp in program.capsule.exports}
    assert ("record", "Product") in exported
    assert ("flow", "calc_total") in exported


def test_capsule_rejected_in_app():
    source = 'spec is "1.0"\n\ncapsule "inventory":\n  exports:\n    record "Product"\n'
    with pytest.raises(Namel3ssError) as excinfo:
        parse(source)
    assert "capsule" in str(excinfo.value).lower()
