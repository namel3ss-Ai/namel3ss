from pathlib import Path

from namel3ss.runtime.storage.sqlite_store import SQLiteStore
from namel3ss.runtime.store.memory_store import MemoryStore
from namel3ss.schema.records import FieldSchema, RecordSchema
from namel3ss.studio.server import build_session_state


APP_SOURCE = 'spec is "1.0"\n\nflow "demo":\n  return "ok"\n'


def _write_app(tmp_path: Path) -> Path:
    app_path = tmp_path / "app.ai"
    app_path.write_text(APP_SOURCE, encoding="utf-8")
    return app_path


def _write_config(tmp_path: Path, db_path: Path) -> None:
    config = (
        "[persistence]\n"
        'target = "sqlite"\n'
        f'db_path = "{db_path.as_posix()}"\n'
    )
    (tmp_path / "namel3ss.toml").write_text(config, encoding="utf-8")


def test_session_state_uses_configured_store(tmp_path: Path) -> None:
    app_path = _write_app(tmp_path)
    db_path = tmp_path / "data.db"
    _write_config(tmp_path, db_path)
    session = build_session_state(app_path)
    assert not isinstance(session.store, MemoryStore)
    assert isinstance(session.store, SQLiteStore)
    assert session.store.db_path == db_path


def test_session_state_persists_records(tmp_path: Path) -> None:
    app_path = _write_app(tmp_path)
    db_path = tmp_path / "data.db"
    _write_config(tmp_path, db_path)
    session = build_session_state(app_path)
    schema = RecordSchema(
        name="Order",
        fields=[FieldSchema(name="order_id", type_name="text")],
    )
    session.store.begin()
    session.store.save(schema, {"order_id": "O-1001"})
    session.store.commit()
    follow_up = build_session_state(app_path)
    records = follow_up.store.find(schema, lambda _rec: True)
    assert any(rec.get("order_id") == "O-1001" for rec in records)
