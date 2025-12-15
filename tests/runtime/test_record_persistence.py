import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.store.memory_store import MemoryStore
from tests.conftest import run_flow


RECORD_DECL = '''record "User":
  email string must be unique
  name string must be present
  age int must be greater than 18

flow "demo":
  save User
'''


def test_save_valid_record_succeeds():
    result = run_flow(RECORD_DECL, initial_state={"user": {"email": "a@b.com", "name": "Ann", "age": 21}})
    assert result.last_value["email"] == "a@b.com"


def test_unique_constraint_fails_with_shared_store():
    store = MemoryStore()
    run_flow(RECORD_DECL, initial_state={"user": {"email": "dup@x.com", "name": "Ann", "age": 21}}, store=store)
    with pytest.raises(Namel3ssError) as exc:
        run_flow(
            RECORD_DECL,
            initial_state={"user": {"email": "dup@x.com", "name": "Bob", "age": 22}},
            store=store,
        )
    assert "unique" in str(exc.value).lower()


def test_presence_length_pattern_errors():
    source = '''record "Doc":
  title string must be present
  slug string must have length at least 3
  tag string must match pattern "^[a-z]+$"

flow "demo":
  save Doc
'''
    with pytest.raises(Namel3ssError) as exc:
        run_flow(source, initial_state={"doc": {"title": None, "slug": "xy", "tag": "Bad-1"}})
    msg = str(exc.value).lower()
    assert "must be present" in msg or "length" in msg or "pattern" in msg


def test_find_query_returns_results():
    source = '''record "User":
  email string must be unique

flow "demo":
  save User
  find User where email is equal to "a@b.com"
'''
    result = run_flow(source, initial_state={"user": {"email": "a@b.com"}})
    assert isinstance(result.last_value, list)
    assert result.last_value[0]["email"] == "a@b.com"
