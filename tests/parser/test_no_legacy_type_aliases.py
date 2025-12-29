import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.parser.core import parse


def test_aliases_allowed_by_default():
    src = '''
spec is "1.0"

record "User":
  field "age" is int
'''
    program = parse(src)
    assert program.records[0].fields[0].type_name == "number"


@pytest.mark.parametrize(
    ("alias", "canonical"),
    [
        ("int", "number"),
        ("string", "text"),
        ("bool", "boolean"),
    ],
)
def test_aliases_rejected_when_strict(alias: str, canonical: str):
    src = f'''
spec is "1.0"

record "User":
  field "age" is {alias}
'''
    with pytest.raises(Namel3ssError) as err:
        parse(src, allow_legacy_type_aliases=False)
    assert canonical in str(err.value)
    assert alias in str(err.value)
