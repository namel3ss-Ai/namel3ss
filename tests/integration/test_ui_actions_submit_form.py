import pytest

from namel3ss.runtime.store.memory_store import MemoryStore
from namel3ss.runtime.ui.actions import handle_action
from tests.conftest import lower_ir_program


PROGRAM = '''record "User":
  email string must be unique
  name string must be present

page "home":
  form is "User"
  table is "User"
'''


def test_submit_form_saves_record_and_updates_ui():
    program = lower_ir_program(PROGRAM)
    store = MemoryStore()
    response = handle_action(
        program,
        action_id="page.home.form.user",
        payload={"values": {"email": "a@b.com", "name": "Ann"}},
        store=store,
    )
    assert response["ok"] is True
    records = store.list_records(program.records[0])
    assert len(records) == 1
    assert records[0]["email"] == "a@b.com"
    table = next(e for e in response["ui"]["pages"][0]["elements"] if e["type"] == "table")
    assert table["rows"][0]["email"] == "a@b.com"


def test_submit_form_returns_validation_errors():
    program = lower_ir_program(PROGRAM)
    store = MemoryStore()
    response = handle_action(
        program,
        action_id="page.home.form.user",
        payload={"values": {"email": "a@b.com"}},
        store=store,
    )
    assert response["ok"] is False
    assert any(err["field"] == "name" and err["code"] == "present" for err in response["errors"])


def test_unique_constraint_violation_returns_error():
    program = lower_ir_program(PROGRAM)
    store = MemoryStore()
    handle_action(
        program,
        action_id="page.home.form.user",
        payload={"values": {"email": "a@b.com", "name": "Ann"}},
        store=store,
    )
    response = handle_action(
        program,
        action_id="page.home.form.user",
        payload={"values": {"email": "a@b.com", "name": "Bob"}},
        store=store,
    )
    assert response["ok"] is False
    assert any(err["code"] == "unique" for err in response["errors"])


def test_submit_form_accepts_flat_payload():
    program = lower_ir_program(PROGRAM)
    store = MemoryStore()
    response = handle_action(
        program,
        action_id="page.home.form.user",
        payload={"email": "a@b.com", "name": "Ann"},
        store=store,
    )
    assert response["ok"] is True
    records = store.list_records(program.records[0])
    assert records[0]["email"] == "a@b.com"


def test_malformed_payload_raises_error():
    program = lower_ir_program(PROGRAM)
    store = MemoryStore()
    with pytest.raises(Exception) as exc:
        handle_action(program, action_id="page.home.form.user", payload="bad", store=store)
    assert "payload was not a json object" in str(exc.value).lower()
