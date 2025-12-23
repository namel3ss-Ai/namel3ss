from namel3ss.runtime.store.memory_store import MemoryStore
from namel3ss.runtime.storage.factory import create_store
from namel3ss.runtime.storage.sqlite_store import SCHEMA_VERSION
from namel3ss.ui.manifest import build_manifest
from tests.conftest import lower_ir_program


SOURCE = 'page "home":\n  title is "hi"\n'


def _program():
    return lower_ir_program(SOURCE)


def test_manifest_persistence_memory(monkeypatch):
    program = _program()
    monkeypatch.delenv("N3_PERSIST", raising=False)
    monkeypatch.delenv("N3_PERSIST_TARGET", raising=False)
    manifest = build_manifest(program, state={}, store=MemoryStore())
    persistence = manifest["ui"]["persistence"]
    assert persistence["enabled"] is False
    assert persistence["kind"] == "memory"
    assert persistence["path"] is None
    assert persistence["schema_version"] is None


def test_manifest_persistence_sqlite(tmp_path, monkeypatch):
    program = _program()
    monkeypatch.setenv("N3_PERSIST_TARGET", "sqlite")
    monkeypatch.chdir(tmp_path)
    store = create_store()
    manifest = build_manifest(program, state={}, store=store)
    if hasattr(store, "close"):
        store.close()
    persistence = manifest["ui"]["persistence"]
    assert persistence["enabled"] is True
    assert persistence["kind"] == "sqlite"
    assert persistence["path"].endswith(".namel3ss/data.db")
    assert persistence["schema_version"] == SCHEMA_VERSION
