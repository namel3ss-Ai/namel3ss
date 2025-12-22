from namel3ss.runtime.storage.sqlite_store import SQLiteStore
from namel3ss.schema.records import FieldSchema, RecordSchema


def _schema():
    return RecordSchema(name="User", fields=[FieldSchema(name="id", type_name="int"), FieldSchema(name="email", type_name="string")])


def test_schema_created_once(tmp_path):
    db = tmp_path / "schema.db"
    schema = _schema()
    store = SQLiteStore(db)
    store.list_records(schema)
    store.close()

    store2 = SQLiteStore(db)
    store2.list_records(schema)
    store2.close()
