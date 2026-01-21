from __future__ import annotations

from types import SimpleNamespace

from namel3ss.config.model import AppConfig
from namel3ss.runtime.data.data_routes import (
    build_data_status_payload,
    build_migrations_plan_payload,
    build_migrations_status_payload,
)
from namel3ss.runtime.data.mysql_backend import MySQLBackend, normalize_mysql_error


def test_data_status_redacts_paths(tmp_path) -> None:
    config = AppConfig()
    config.persistence.target = "sqlite"
    config.persistence.db_path = str(tmp_path / "data.db")
    payload = build_data_status_payload(config, project_root=tmp_path, app_path=tmp_path / "app.ai")
    backend = payload["backend"]
    assert backend["target"] == "sqlite"
    assert backend["descriptor"] == "data.db"


def test_mysql_backend_type_mapping_and_errors() -> None:
    backend = MySQLBackend()
    assert backend.sql_type_for("text") == "TEXT"
    assert backend.sql_type_for("integer") == "BIGINT"
    assert backend.sql_type_for("boolean") == "TINYINT(1)"
    assert backend.sql_type_for("number") == "DECIMAL(38,18)"

    class DummyError(Exception):
        pass

    assert normalize_mysql_error(DummyError(1062, "duplicate")) == "duplicate key"
    assert normalize_mysql_error(DummyError(1146, "missing table")) == "missing table"
    assert normalize_mysql_error(DummyError(1054, "unknown column")) == "unknown column"
    assert normalize_mysql_error(DummyError(9999, "other")) == "mysql error 9999"
    assert normalize_mysql_error(DummyError("oops")) == "mysql error"


def test_migration_routes_payloads_are_stable(tmp_path) -> None:
    program = SimpleNamespace(records=[])
    status_one = build_migrations_status_payload(program, project_root=tmp_path)
    status_two = build_migrations_status_payload(program, project_root=tmp_path)
    assert status_one == status_two

    plan_one = build_migrations_plan_payload(program, project_root=tmp_path)
    plan_two = build_migrations_plan_payload(program, project_root=tmp_path)
    assert plan_one == plan_two
