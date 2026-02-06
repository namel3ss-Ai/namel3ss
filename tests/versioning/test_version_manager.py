from __future__ import annotations

from pathlib import Path

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.versioning import (
    VersionConfig,
    add_version,
    deprecate_version,
    list_versions,
    load_version_config,
    remove_version,
    resolve_target_version,
    save_version_config,
)


def _write_app(tmp_path: Path) -> Path:
    app = tmp_path / "app.ai"
    app.write_text('spec is "1.0"\n\nflow "demo":\n  return "ok"\n', encoding="utf-8")
    return app


def test_version_lifecycle_roundtrip_and_resolve(tmp_path: Path) -> None:
    app = _write_app(tmp_path)
    config = VersionConfig(routes={}, flows={}, models={})
    config = add_version(config, kind="route", entity_name="list_users", version="1.0")
    config = add_version(config, kind="route", entity_name="list_users", version="2.0")
    config = deprecate_version(
        config,
        kind="route",
        entity_name="list_users",
        version="1.0",
        replacement="2.0",
        deprecation_date="2026-06-01",
    )
    save_version_config(app.parent, app, config)

    loaded = load_version_config(app.parent, app)
    rows = list_versions(loaded, kind="routes")
    assert rows == [
        {
            "kind": "routes",
            "entity": "list_users",
            "version": "1.0",
            "status": "deprecated",
            "target": None,
            "replacement": "2.0",
            "deprecation_date": "2026-06-01",
        },
        {
            "kind": "routes",
            "entity": "list_users",
            "version": "2.0",
            "status": "active",
            "target": None,
            "replacement": None,
            "deprecation_date": None,
        },
    ]

    latest = resolve_target_version(loaded, kind="route", target_name="list_users", requested_version=None)
    assert latest is not None
    assert latest.entry.version == "2.0"
    assert latest.entry.status == "active"

    requested = resolve_target_version(loaded, kind="route", target_name="list_users", requested_version="1.0")
    assert requested is not None
    assert requested.entry.version == "1.0"
    assert requested.entry.status == "deprecated"
    assert requested.requested_removed is False


def test_remove_last_active_requires_replacement(tmp_path: Path) -> None:
    _ = _write_app(tmp_path)
    config = VersionConfig(routes={}, flows={}, models={})
    config = add_version(config, kind="flow", entity_name="summarise", version="1.0")
    with pytest.raises(Namel3ssError):
        remove_version(config, kind="flow", entity_name="summarise", version="1.0")


def test_semver_precedence_is_used_for_latest_resolution() -> None:
    config = VersionConfig(routes={}, flows={}, models={})
    config = add_version(config, kind="route", entity_name="users", version="1.9.0")
    config = add_version(config, kind="route", entity_name="users", version="1.10.0")
    config = add_version(config, kind="route", entity_name="users", version="2.0.0-rc.1")
    config = add_version(config, kind="route", entity_name="users", version="2.0.0")

    latest = resolve_target_version(config, kind="route", target_name="users", requested_version=None)
    assert latest is not None
    assert latest.entry.version == "2.0.0"

    rows = list_versions(config, kind="routes")
    assert [row["version"] for row in rows] == ["1.9.0", "1.10.0", "2.0.0-rc.1", "2.0.0"]
