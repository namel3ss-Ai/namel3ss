from namel3ss.format.formatter import format_source


def test_formatter_preserves_fields_block():
    source = '''record "Order":
  fields:
    order_id is text must be present
    customer is text
'''
    formatted = format_source(source)
    assert "fields:" in formatted
    assert "order_id is text must be present" in formatted
    assert "customer is text" in formatted
    assert 'field "order_id"' not in formatted


def test_formatter_fields_block_is_idempotent():
    source = '''record "Order":
  fields:
    order_id is text
    customer is text
    total is number
'''
    once = format_source(source)
    twice = format_source(once)
    assert once == twice


def test_formatter_keeps_reserved_keyword_fields_legacy():
    source = '''record "ConversionRequest":
  field "from" is text
  field "to" is text
  field "amount" is number
'''
    formatted = format_source(source)
    assert "fields:" not in formatted
    assert 'field "to" is text' in formatted
