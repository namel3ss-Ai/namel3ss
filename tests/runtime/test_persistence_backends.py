from __future__ import annotations

import json

from namel3ss.config.model import AppConfig
from namel3ss.runtime.persistence import (
    describe_persistence_backend,
    export_persistence_state,
    inspect_persistence_state_key,
    list_persistence_state_keys,
)


def test_memory_backend_descriptor_is_deterministic(tmp_path) -> None:
    config = AppConfig()
    config.persistence.target = "memory"
    first = describe_persistence_backend(config, project_root=tmp_path, app_path=tmp_path / "app.ai")
    second = describe_persistence_backend(config, project_root=tmp_path, app_path=tmp_path / "app.ai")
    assert first == second
    assert first["target"] == "memory"
    assert first["durable"] is False


def test_file_backend_lists_and_exports_known_state_keys(tmp_path) -> None:
    config = AppConfig()
    config.persistence.target = "sqlite"
    root = tmp_path / ".namel3ss"
    (root / "migrations").mkdir(parents=True)
    (root / "run").mkdir(parents=True)
    (root / "migrations" / "state.json").write_text(
        json.dumps({"last_plan_id": "plan-1", "applied_plan_id": "plan-1"}, sort_keys=True),
        encoding="utf-8",
    )
    (root / "run" / "last.json").write_text(json.dumps({"ok": True}, sort_keys=True), encoding="utf-8")
    keys = list_persistence_state_keys(config, project_root=tmp_path, app_path=tmp_path / "app.ai")
    assert keys == ["persistence.backend", "migrations.state", "run.last"]
    exported = export_persistence_state(config, project_root=tmp_path, app_path=tmp_path / "app.ai")
    assert exported["keys"] == keys
    assert exported["items"]["migrations.state"]["applied_plan_id"] == "plan-1"


def test_postgres_backend_descriptor_requires_network(tmp_path) -> None:
    config = AppConfig()
    config.persistence.target = "postgres"
    config.persistence.database_url = "postgres://demo:demo@localhost/demo"
    descriptor = describe_persistence_backend(config, project_root=tmp_path, app_path=tmp_path / "app.ai")
    assert descriptor["target"] == "postgres"
    assert descriptor["requires_network"] is True
    assert descriptor["enabled"] is True
    value = inspect_persistence_state_key(
        config,
        project_root=tmp_path,
        app_path=tmp_path / "app.ai",
        key="persistence.backend",
    )
    assert isinstance(value, dict)
    assert value["target"] == "postgres"
