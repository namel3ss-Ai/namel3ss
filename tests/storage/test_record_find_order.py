from pathlib import Path

from namel3ss.runtime.store.memory_store import MemoryStore
from namel3ss.runtime.storage.sqlite_store import SQLiteStore
from namel3ss.schema.records import FieldSchema, RecordSchema


def _schema() -> RecordSchema:
    return RecordSchema(
        name="Item",
        fields=[
            FieldSchema(name="id", type_name="number"),
            FieldSchema(name="name", type_name="text"),
        ],
    )


def test_memory_store_find_returns_sorted_ids() -> None:
    store = MemoryStore()
    schema = _schema()
    store.save(schema, {"id": 10, "name": "Ten"})
    store.save(schema, {"id": 2, "name": "Two"})
    store.save(schema, {"id": 7, "name": "Seven"})
    rows = store.find(schema, lambda _rec: True)
    assert [row["id"] for row in rows] == [2, 7, 10]


def test_sqlite_store_find_returns_sorted_ids(tmp_path: Path) -> None:
    db_path = tmp_path / "data.db"
    store = SQLiteStore(db_path)
    schema = _schema()
    store.save(schema, {"name": "Alpha"})
    store.save(schema, {"name": "Beta"})
    store.save(schema, {"name": "Gamma"})
    rows = store.find(schema, lambda _rec: True)
    assert [row["id"] for row in rows] == [1, 2, 3]
    store.close()


def test_sqlite_store_respects_explicit_ids(tmp_path: Path) -> None:
    db_path = tmp_path / "data.db"
    store = SQLiteStore(db_path)
    schema = _schema()
    store.save(schema, {"id": 10, "name": "Ten"})
    store.save(schema, {"id": 2, "name": "Two"})
    rows = store.find(schema, lambda _rec: True)
    assert [row["id"] for row in rows] == [2, 10]
    store.close()
