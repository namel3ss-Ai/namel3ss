import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.audit.recorder import audit_schema
from namel3ss.runtime.records import service as records_service
from namel3ss.runtime.store.memory_store import MemoryStore
from tests.conftest import run_flow


TENANT_SOURCE = '''identity "user":
  field "org_id" is text must be present

record "Item":
  field "name" is text
  tenant_key is identity.org_id

flow "seed":
  save Item

flow "list":
  find Item where name is equal to "Widget"
'''


def test_tenant_scoping_filters_records():
    store = MemoryStore()
    run_flow(
        TENANT_SOURCE,
        flow_name="seed",
        initial_state={"item": {"name": "Widget"}},
        store=store,
        identity={"org_id": "acme"},
    )
    result = run_flow(TENANT_SOURCE, flow_name="list", store=store, identity={"org_id": "acme"})
    assert len(result.last_value) == 1
    other = run_flow(TENANT_SOURCE, flow_name="list", store=store, identity={"org_id": "other"})
    assert other.last_value == []


def test_tenant_missing_identity_errors():
    store = MemoryStore()
    with pytest.raises(Namel3ssError) as exc:
        run_flow(
            TENANT_SOURCE,
            flow_name="seed",
            initial_state={"item": {"name": "Widget"}},
            store=store,
        )
    message = str(exc.value).lower()
    assert "identity field" in message or "org_id" in message


def test_ttl_expires_records(monkeypatch):
    source = '''record "Session":
  field "token" is text
  persisted:
    ttl_hours is 1

flow "seed":
  save Session

flow "list":
  find Session where token is equal to "abc"
'''
    store = MemoryStore()
    monkeypatch.setattr(records_service.time, "time", lambda: 0)
    run_flow(
        source,
        flow_name="seed",
        initial_state={"session": {"token": "abc"}},
        store=store,
    )
    monkeypatch.setattr(records_service.time, "time", lambda: 7200)
    result = run_flow(source, flow_name="list", store=store)
    assert result.last_value == []


def test_audited_flow_writes_audit_log():
    source = '''flow "demo": audited
  set state.token is "abc"
  return "ok"
'''
    store = MemoryStore()
    result = run_flow(
        source,
        initial_state={"password": "shh"},
        store=store,
        identity={"email": "dev@example.com", "role": "admin", "secret": "nope"},
    )
    assert result.last_value == "ok"
    records = store.list_records(audit_schema())
    assert records
    entry = records[0]
    assert entry["flow"] == "demo"
    assert entry["actor"]["email"] == "dev@example.com"
    assert entry["actor"]["role"] == "admin"
    assert "secret" not in entry["actor"]
    assert entry["before"]["password"] == "***"
    assert entry["after"]["token"] == "***"
