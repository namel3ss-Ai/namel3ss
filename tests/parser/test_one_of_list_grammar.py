from dataclasses import fields, is_dataclass

from tests.conftest import parse_program


def _strip_positions(value):
    if isinstance(value, list):
        return [_strip_positions(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_strip_positions(item) for item in value)
    if is_dataclass(value):
        data = {}
        for field in fields(value):
            field_value = getattr(value, field.name)
            if field.name in {"line", "column"}:
                data[field.name] = None
            else:
                data[field.name] = _strip_positions(field_value)
        return type(value)(**data)
    return value


def _requires_expr(source: str):
    program = parse_program(source)
    return program.flows[0].requires


def test_one_of_list_inline_matches_legacy_brackets():
    inline = 'flow "demo": requires identity.role is one of "admin", "staff"\n'
    legacy = 'flow "demo": requires identity.role is one of ["admin", "staff"]\n'
    assert _strip_positions(_requires_expr(inline)) == _strip_positions(_requires_expr(legacy))


def test_one_of_list_block_matches_inline():
    inline = 'flow "demo": requires identity.role is one of "admin", "staff"\n'
    block = '''flow "demo": requires identity.role is one of:
  "admin",
  "staff"
'''
    assert _strip_positions(_requires_expr(inline)) == _strip_positions(_requires_expr(block))
