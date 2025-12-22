from namel3ss.runtime.storage.sqlite_store import SQLiteStore
from namel3ss.schema.records import FieldSchema, RecordSchema


def _schema():
    return RecordSchema(name="Item", fields=[FieldSchema(name="id", type_name="int"), FieldSchema(name="name", type_name="string")])


def test_transaction_rollback(tmp_path):
    store = SQLiteStore(tmp_path / "tx.db")
    schema = _schema()
    store.begin()
    store.save(schema, {"name": "one"})
    store.rollback()
    rows = store.list_records(schema)
    assert rows == []
    store.close()
