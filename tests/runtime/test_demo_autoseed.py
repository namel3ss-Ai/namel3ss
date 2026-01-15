from __future__ import annotations

from pathlib import Path

from namel3ss.cli.app_loader import load_program
from namel3ss.runtime.service_runner import ServiceRunner
from namel3ss.runtime.storage.sqlite_store import SQLiteStore


APP_SOURCE = '''spec is "1.0"

record "Order":
  field "order_id" is text must be present

flow "seed_demo":
  find "Order" where true
  let existing is list length of order_results
  if existing is greater than 0:
    return "seeded"
  set state.order with:
    order_id is "O-1"
  create "Order" with state.order as order
  return "seeded"

page "home":
  title is "Demo"
'''


def _write_app(root: Path) -> Path:
    app_path = root / "app.ai"
    app_path.write_text(APP_SOURCE, encoding="utf-8")
    return app_path


def _order_schema(app_path: Path):
    program, _ = load_program(app_path.as_posix())
    return next(record for record in program.records if record.name == "Order")


def _count_orders(db_path: Path, schema) -> int:
    store = SQLiteStore(db_path)
    return len(store.list_records(schema))


def test_demo_autoseed_happens_once_when_empty(tmp_path, monkeypatch):
    app_path = _write_app(tmp_path)
    demo_dir = tmp_path / ".namel3ss"
    demo_dir.mkdir()
    (demo_dir / "demo.json").write_text('{"name":"demo"}', encoding="utf-8")
    db_path = tmp_path / "demo.db"
    monkeypatch.setenv("N3_PERSIST_TARGET", "sqlite")
    monkeypatch.setenv("N3_DB_PATH", str(db_path))

    runner = ServiceRunner(app_path, "service", port=0, auto_seed=True)
    try:
        runner.start(background=True)
    finally:
        runner.shutdown()

    schema = _order_schema(app_path)
    assert _count_orders(db_path, schema) == 1

    runner = ServiceRunner(app_path, "service", port=0, auto_seed=True)
    try:
        runner.start(background=True)
    finally:
        runner.shutdown()

    assert _count_orders(db_path, schema) == 1


def test_no_autoseed_for_non_demo(tmp_path, monkeypatch):
    app_path = _write_app(tmp_path)
    db_path = tmp_path / "demo.db"
    monkeypatch.setenv("N3_PERSIST_TARGET", "sqlite")
    monkeypatch.setenv("N3_DB_PATH", str(db_path))

    runner = ServiceRunner(app_path, "service", port=0, auto_seed=True)
    try:
        runner.start(background=True)
    finally:
        runner.shutdown()

    schema = _order_schema(app_path)
    assert _count_orders(db_path, schema) == 0
