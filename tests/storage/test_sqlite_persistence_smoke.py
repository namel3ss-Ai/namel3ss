from pathlib import Path

from namel3ss.runtime.storage.sqlite_store import SQLiteStore
from namel3ss.schema.records import FieldSchema, RecordSchema


def _schema():
    return RecordSchema(name="Note", fields=[FieldSchema(name="id", type_name="int"), FieldSchema(name="title", type_name="string")])


def test_records_persist_across_store_instances(tmp_path):
    db = tmp_path / "data.db"
    schema = _schema()
    store = SQLiteStore(db)
    store.begin()
    store.save(schema, {"title": "hello"})
    store.commit()
    store.close()

    store2 = SQLiteStore(db)
    rows = store2.list_records(schema)
    assert len(rows) == 1
    assert rows[0]["title"] == "hello"
    assert rows[0]["id"] == 1
    store2.close()
