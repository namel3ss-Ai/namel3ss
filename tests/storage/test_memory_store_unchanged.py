from namel3ss.runtime.store.memory_store import MemoryStore
from namel3ss.schema.records import FieldSchema, RecordSchema


def _schema():
    return RecordSchema(name="Task", fields=[FieldSchema(name="id", type_name="int"), FieldSchema(name="title", type_name="string")])


def test_memory_store_behavior_stable():
    store = MemoryStore()
    schema = _schema()
    saved = store.save(schema, {"title": "hi"})
    assert saved["id"] == 1
    rows = store.list_records(schema)
    assert rows[0]["title"] == "hi"
    store.begin()
    store.save(schema, {"title": "bye"})
    store.rollback()
    rows_after = store.list_records(schema)
    assert len(rows_after) == 1
