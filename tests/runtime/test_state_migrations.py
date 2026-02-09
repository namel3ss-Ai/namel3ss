from __future__ import annotations

from namel3ss.config.model import AppConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.migrations import (
    apply_migrations,
    build_migration_status,
    require_migration_ready,
)
from tests.conftest import lower_ir_program


def _program_with_record():
    source = '''
record "Item":
  name text

spec is "1.0"

flow "demo":
  return "ok"
'''.lstrip()
    return lower_ir_program(source)


def test_migration_status_is_deterministic(tmp_path) -> None:
    program = _program_with_record()
    one = build_migration_status(program, project_root=tmp_path)
    two = build_migration_status(program, project_root=tmp_path)
    assert one == two
    assert one["state_schema_version"] == "state_schema@1"


def test_apply_migrations_dry_run_reports_status_only(tmp_path) -> None:
    program = _program_with_record()
    config = AppConfig()
    result = apply_migrations(program, project_root=tmp_path, config=config, dry_run=True)
    assert result["ok"] is True
    assert result["dry_run"] is True
    assert result["applied"] is False
    status = result["migration_status"]
    assert isinstance(status, dict)
    assert status["schema_version"] == "migration_status@1"


def test_require_migration_ready_blocks_pending_without_override(tmp_path) -> None:
    program = _program_with_record()
    status = build_migration_status(program, project_root=tmp_path)
    if not status["pending"]:
        return
    try:
        require_migration_ready(program, project_root=tmp_path, allow_pending=False)
    except Namel3ssError as err:
        assert "pending migrations" in str(err).lower()
    else:
        raise AssertionError("Expected require_migration_ready to block pending migrations")
