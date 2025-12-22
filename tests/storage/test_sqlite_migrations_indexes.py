import sqlite3

from namel3ss.runtime.storage.sqlite_store import SQLiteStore, SCHEMA_VERSION
from namel3ss.schema.records import FieldConstraint, FieldSchema, RecordSchema
from namel3ss.runtime.store.memory_store import Contains


def _user_schema():
    return RecordSchema(
        name="User",
        fields=[
            FieldSchema(name="id", type_name="int"),
            FieldSchema(name="email", type_name="string", constraint=FieldConstraint(kind="unique")),
            FieldSchema(name="name", type_name="string"),
        ],
    )


def _index_names(conn, table: str):
    return [row[1] for row in conn.execute(f"PRAGMA index_list('{table}')").fetchall()]


def test_migration_bumps_version_and_adds_unique_index(tmp_path):
    db = tmp_path / "data.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE schema_version (version INTEGER NOT NULL)")
    conn.execute("INSERT INTO schema_version (version) VALUES (1)")
    conn.execute("CREATE TABLE user (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT, name TEXT)")
    conn.commit()
    conn.close()

    schema = _user_schema()
    store = SQLiteStore(db)
    store.save(schema, {"email": "a@example.com", "name": "A"})
    store.close()

    conn = sqlite3.connect(db)
    version = conn.execute("SELECT version FROM schema_version").fetchone()[0]
    assert version == SCHEMA_VERSION
    indexes = _index_names(conn, "user")
    assert "idx_user_email_uniq" in indexes
    conn.close()


def test_unique_index_exists_and_used_for_lookup(tmp_path):
    db = tmp_path / "data.db"
    schema = _user_schema()
    store = SQLiteStore(db)
    store.save(schema, {"email": "first@example.com", "name": "First"})
    store.save(schema, {"email": "second@example.com", "name": "Second"})
    indexes = [row["name"] for row in store.conn.execute("PRAGMA index_list('user')").fetchall()]
    assert "idx_user_email_uniq" in indexes
    plan = store.conn.execute("EXPLAIN QUERY PLAN SELECT * FROM user WHERE email = ?", ("first@example.com",)).fetchone()
    assert "idx_user_email_uniq" in plan[3]
    plan_pk = store.conn.execute("EXPLAIN QUERY PLAN SELECT * FROM user WHERE id = ?", (1,)).fetchone()
    assert "PRIMARY KEY" in plan_pk[3]
    store.close()


def test_filtered_find_uses_where_clause(tmp_path):
    db = tmp_path / "data.db"
    schema = _user_schema()
    store = SQLiteStore(db)
    for i in range(200):
        store.save(schema, {"email": f"user{i}@example.com", "name": f"User {i}"})
    exact = store.find(schema, {"email": "user10@example.com"})
    assert len(exact) == 1
    assert exact[0]["email"] == "user10@example.com"
    partial = store.find(schema, {"name": Contains("User 1")})
    assert partial
    plan = store.conn.execute("EXPLAIN QUERY PLAN SELECT * FROM user WHERE email = ?", ("user10@example.com",)).fetchone()
    assert "idx_user_email_uniq" in plan[3]
    store.close()
