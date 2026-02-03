import pytest

from namel3ss.errors.base import Namel3ssError
from tests.conftest import lower_ir_program, parse_program


def test_form_references_missing_record():
    source = '''flow "create_user":
  return "ok"

page "home":
  form is "User"
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "unknown record" in str(exc.value).lower()


def test_button_calls_missing_flow():
    source = '''page "home":
  button "Create user":
    calls flow "create_user"
    '''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    message = str(exc.value).lower()
    assert "unknown flow" in message
    assert "calls flow" in message
    assert "runs" in message


def test_text_input_requires_flow_input():
    source = '''flow "answer":
  return "ok"

page "home":
  input text as question
    send to flow "answer"
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "text input" in str(exc.value).lower()
    assert "input" in str(exc.value).lower()


def test_text_input_requires_text_field():
    source = '''contract flow "answer":
  input:
    question is number
  output:
    result is text

flow "answer":
  return "ok"

page "home":
  input text as question
    send to flow "answer"
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "text" in str(exc.value).lower()
    assert "question" in str(exc.value).lower()


def test_illegal_statement_in_page_block_errors():
    source = '''page "home":
  let x is 1
'''
    with pytest.raises(Namel3ssError) as exc:
        parse_program(source)
    assert "declarative" in str(exc.value).lower()


def test_table_columns_unknown_field_errors():
    source = '''record "Order":
  name text

page "home":
  table is "Order":
    columns:
      include missing
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "unknown field" in str(exc.value).lower()


def test_table_pagination_requires_positive_int():
    source = '''record "Order":
  name text

page "home":
  table is "Order":
    pagination:
      page_size is 0
'''
    with pytest.raises(Namel3ssError) as exc:
        parse_program(source)
    assert "page_size must be a positive integer" in str(exc.value).lower()


def test_state_table_requires_columns():
    source = '''page "home":
  table from state metrics
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "state tables require columns" in str(exc.value).lower()


def test_state_table_disallows_sorting():
    source = '''page "home":
  table from state metrics:
    columns:
      include name
    sort:
      by is name
      order is asc
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "state tables do not support sorting" in str(exc.value).lower()


def test_row_action_unknown_flow_errors():
    source = '''record "Order":
  name text

page "home":
  table is "Order":
    row_actions:
      row_action "Open":
        calls flow "missing_flow"
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "unknown flow" in str(exc.value).lower()


def test_card_action_unknown_flow_errors():
    source = '''page "home":
  card "Summary":
    actions:
      action "Run":
        calls flow "missing_flow"
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "unknown flow" in str(exc.value).lower()


def test_card_action_duplicate_labels_error():
    source = '''flow "go":
  return "ok"

page "home":
  card "Summary":
    actions:
      action "Run":
        calls flow "go"
      action "Run":
        calls flow "go"
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "duplicated" in str(exc.value).lower()


def test_list_item_unknown_field_errors():
    source = '''record "Order":
  name text

page "home":
  list is "Order":
    item:
      primary is missing
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "unknown field" in str(exc.value).lower()


def test_list_icon_requires_variant():
    source = '''record "Order":
  name text
  icon text

page "home":
  list is "Order":
    item:
      primary is name
      icon is icon
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "requires variant" in str(exc.value).lower()


def test_list_icon_requires_text():
    source = '''record "Order":
  name text
  icon number

page "home":
  list is "Order":
    variant is icon
    item:
      primary is name
      icon is icon
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "must be text" in str(exc.value).lower()


def test_list_action_unknown_flow_errors():
    source = '''record "Order":
  name text

page "home":
  list is "Order":
    actions:
      action "Open":
        calls flow "missing_flow"
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "unknown flow" in str(exc.value).lower()


def test_state_list_requires_item_mapping():
    source = '''page "home":
  list from state items
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "state lists require item mapping" in str(exc.value).lower()


def test_state_list_disallows_actions():
    source = '''flow "open_item":
  return "ok"

page "home":
  list from state items:
    item:
      primary is name
    actions:
      action "Open":
        calls flow "open_item"
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "state lists do not support actions" in str(exc.value).lower()


def test_chat_composer_unknown_flow_errors():
    source = '''page "home":
  chat:
    composer calls flow "missing_flow"
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "unknown flow" in str(exc.value).lower()


def test_form_group_unknown_field_errors():
    source = '''record "User":
  name text

page "home":
  form is "User":
    groups:
      group "Main":
        field missing
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "unknown field" in str(exc.value).lower()


def test_form_group_duplicate_field_errors():
    source = '''record "User":
  name text
  email text

page "home":
  form is "User":
    groups:
      group "Main":
        field name
      group "Other":
        field name
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "more than once" in str(exc.value).lower()


def test_form_field_config_unknown_field_errors():
    source = '''record "User":
  name text

page "home":
  form is "User":
    fields:
      field missing:
        help is "Nope"
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "not part of record" in str(exc.value).lower()


def test_modal_duplicate_labels_error():
    source = '''page "home":
  modal "Confirm":
    text is "One"
  modal "Confirm":
    text is "Two"
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "duplicated" in str(exc.value).lower()


def test_chart_requires_table_or_list():
    source = '''record "Metric":
  name text
  value number

page "home":
  chart is "Metric"
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "paired" in str(exc.value).lower()


def test_chart_invalid_type_errors():
    source = '''record "Metric":
  name text
  value number

page "home":
  table is "Metric"
  chart is "Metric":
    type is "pie"
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "not supported" in str(exc.value).lower()


def test_chart_unknown_field_errors():
    source = '''record "Metric":
  name text
  value number

page "home":
  table is "Metric"
  chart is "Metric":
    x is missing
    y is value
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "not part of record" in str(exc.value).lower()


def test_chart_state_source_must_match_table_list():
    source = '''record "Metric":
  name text
  value number

page "home":
  table is "Metric"
  chart from is state.other:
    type is summary
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "paired" in str(exc.value).lower()


def test_drawer_duplicate_labels_error():
    source = '''page "home":
  drawer "Info":
    text is "One"
  drawer "Info":
    text is "Two"
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "duplicated" in str(exc.value).lower()


def test_action_unknown_modal_errors():
    source = '''page "home":
  card "Actions":
    actions:
      action "Open":
        opens modal "Missing"
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "unknown modal" in str(exc.value).lower()


def test_link_unknown_page_errors():
    source = '''page "home":
  link "Settings" to page "Settings"
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "unknown page" in str(exc.value).lower()
