import pytest

from namel3ss.errors.base import Namel3ssError
from tests.conftest import parse_program


def _field_signature(record):
    return [(field.name, field.type_name, field.constraint.kind if field.constraint else None) for field in record.fields]


def test_fields_block_desugars_like_field_lines():
    block_source = '''record "Order":
  fields:
    order_id is text must be present
    customer is text
    total_usd is number
'''
    legacy_source = '''record "Order":
  field "order_id" is text must be present
  field "customer" is text
  field "total_usd" is number
'''
    block_record = parse_program(block_source).records[0]
    legacy_record = parse_program(legacy_source).records[0]
    assert _field_signature(block_record) == _field_signature(legacy_record)


def test_fields_block_duplicate_fields_error():
    source = '''record "Order":
  fields:
    order_id is text
    order_id is text
'''
    with pytest.raises(Namel3ssError) as exc:
        parse_program(source)
    assert "more than once" in str(exc.value)


def test_fields_block_duplicate_across_styles_error():
    source = '''record "Order":
  fields:
    order_id is text
  field "order_id" is text
'''
    with pytest.raises(Namel3ssError) as exc:
        parse_program(source)
    assert "more than once" in str(exc.value)


def test_fields_block_empty_error():
    source = 'record "Order":\n  fields:\n'
    with pytest.raises(Namel3ssError) as exc:
        parse_program(source)
    assert "Fields block has no fields" in str(exc.value)


def test_fields_block_invalid_identifier_error():
    source = 'record "Order":\n  fields:\n    field "email" is text\n'
    with pytest.raises(Namel3ssError) as exc:
        parse_program(source)
    assert "field keyword" in str(exc.value)
