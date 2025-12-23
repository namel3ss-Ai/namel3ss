import os

import pytest

from namel3ss.runtime.storage.base import RecordScope
from namel3ss.runtime.storage.postgres_store import PostgresStore
from namel3ss.runtime.storage.sqlite_store import SQLiteStore
from namel3ss.schema.records import FieldSchema, RecordSchema, TENANT_KEY_FIELD


def _schema() -> RecordSchema:
    return RecordSchema(
        name="Item",
        fields=[FieldSchema(name="name", type_name="text")],
        tenant_key=["org_id"],
    )


def test_sqlite_tenant_scoping(tmp_path):
    store = SQLiteStore(tmp_path / "data.db")
    schema = _schema()
    store.save(schema, {"name": "Widget", TENANT_KEY_FIELD: "acme"})
    store.save(schema, {"name": "Widget", TENANT_KEY_FIELD: "other"})
    scope = RecordScope(tenant_value="acme")
    rows = store.find(schema, {"name": "Widget"}, scope=scope)
    assert len(rows) == 1
    assert rows[0]["name"] == "Widget"
    store.close()


@pytest.mark.skipif(not os.getenv("N3_TEST_DATABASE_URL"), reason="N3_TEST_DATABASE_URL not set")
def test_postgres_tenant_scoping():
    pytest.importorskip("psycopg")
    store = PostgresStore(os.environ["N3_TEST_DATABASE_URL"])
    store.clear()
    schema = _schema()
    store.save(schema, {"name": "Widget", TENANT_KEY_FIELD: "acme"})
    store.save(schema, {"name": "Widget", TENANT_KEY_FIELD: "other"})
    scope = RecordScope(tenant_value="acme")
    rows = store.find(schema, {"name": "Widget"}, scope=scope)
    assert len(rows) == 1
    assert rows[0]["name"] == "Widget"
    store.clear()
    store.close()
