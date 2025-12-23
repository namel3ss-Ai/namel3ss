from namel3ss.cli.main import main
from namel3ss.runtime.storage.factory import create_store
from namel3ss.runtime.storage.sqlite_store import SCHEMA_VERSION
from tests.conftest import lower_ir_program


APP_SOURCE = '''record "User":
  email string must be present

page "home":
  title is "Hi"
'''


def _write_app(tmp_path):
    path = tmp_path / "app.ai"
    path.write_text(APP_SOURCE, encoding="utf-8")
    return path


def _user_schema():
    program = lower_ir_program(APP_SOURCE)
    return next(rec for rec in program.records if rec.name == "User")


def _seed_sqlite(tmp_path, monkeypatch):
    path = _write_app(tmp_path)
    monkeypatch.setenv("N3_PERSIST_TARGET", "sqlite")
    monkeypatch.chdir(tmp_path)
    store = create_store()
    schema = _user_schema()
    store.save(schema, {"email": "a@example.com"})
    store.save_state({"ready": True})
    if hasattr(store, "close"):
        store.close()
    return path, schema


def test_data_status_project_root(tmp_path, capsys, monkeypatch):
    path = _write_app(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("N3_PERSIST", raising=False)
    monkeypatch.delenv("N3_PERSIST_TARGET", raising=False)
    code = main(["data"])
    out = capsys.readouterr().out.lower()
    assert code == 0
    assert "store kind: memory" in out
    assert "persistence enabled: false" in out
    assert "n3_persist_target=sqlite" in out


def test_data_status_file_first(tmp_path, capsys, monkeypatch):
    path = _write_app(tmp_path)
    monkeypatch.setenv("N3_PERSIST_TARGET", "sqlite")
    monkeypatch.chdir(tmp_path)
    code = main([str(path), "data"])
    out = capsys.readouterr().out
    assert code == 0
    assert "Store kind: sqlite" in out
    assert ".namel3ss/data.db" in out
    assert f"Schema version: {SCHEMA_VERSION}" in out


def test_data_reset_requires_confirmation(tmp_path, capsys, monkeypatch):
    path, schema = _seed_sqlite(tmp_path, monkeypatch)
    monkeypatch.setattr("builtins.input", lambda _: "NO")
    code = main([str(path), "data", "reset"])
    out = capsys.readouterr().out
    assert code == 1
    store = create_store()
    records = store.list_records(schema)
    if hasattr(store, "close"):
        store.close()
    assert records
    assert "reset aborted" in out.lower()


def test_data_reset_clears_sqlite(tmp_path, capsys, monkeypatch):
    path, schema = _seed_sqlite(tmp_path, monkeypatch)
    code = main([str(path), "data", "reset", "--yes"])
    out = capsys.readouterr().out.lower()
    assert code == 0
    store = create_store()
    records = store.list_records(schema)
    state = store.load_state()
    if hasattr(store, "close"):
        store.close()
    assert records == []
    assert state == {}
    assert "reset at" in out
    assert str(SCHEMA_VERSION) in out


def test_persist_status_alias_still_works(tmp_path, capsys, monkeypatch):
    path = _write_app(tmp_path)
    monkeypatch.chdir(tmp_path)
    code = main([str(path), "persist", "status"])
    out = capsys.readouterr().out.lower()
    assert code == 0
    assert "store kind: memory" in out
