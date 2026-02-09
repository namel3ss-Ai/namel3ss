from __future__ import annotations

import json
from pathlib import Path

from namel3ss.config.model import AppConfig
from namel3ss.runtime.persistence.backend_base import PersistenceBackendDescriptor
from namel3ss.runtime.persistence_paths import resolve_persistence_root
from namel3ss.runtime.storage.factory import DEFAULT_DB_PATH


_STATE_PATHS: tuple[tuple[str, str], ...] = (
    ("migrations.state", ".namel3ss/migrations/state.json"),
    ("run.last", ".namel3ss/run/last.json"),
    ("schema.last", ".namel3ss/schema/last.json"),
    ("audit.last.bundle", ".namel3ss/audit/last/bundle.json"),
    ("audit.last.artifact", ".namel3ss/audit/last/run_artifact.json"),
)


class FilePersistenceBackend:
    name = "file"

    def describe(
        self,
        config: AppConfig,
        *,
        project_root: Path | None,
        app_path: Path | None,
    ) -> PersistenceBackendDescriptor:
        raw_path = str(config.persistence.db_path or DEFAULT_DB_PATH)
        db_path = Path(raw_path)
        descriptor = db_path.name if db_path.name else db_path.as_posix()
        replicas = tuple(str(item) for item in (config.persistence.replica_urls or ()) if str(item).strip())
        return PersistenceBackendDescriptor(
            target="file",
            kind="sqlite",
            enabled=True,
            durable=True,
            deterministic_ordering=True,
            descriptor=descriptor,
            requires_network=False,
            replicas=tuple(sorted(replicas)),
        )

    def list_state_keys(
        self,
        config: AppConfig,
        *,
        project_root: Path | None,
        app_path: Path | None,
    ) -> list[str]:
        keys = ["persistence.backend"]
        root = _resolve_root(project_root=project_root, app_path=app_path)
        if root is None:
            return keys
        for key, rel_path in _STATE_PATHS:
            if (root / rel_path).exists():
                keys.append(key)
        return keys

    def inspect_state_key(
        self,
        config: AppConfig,
        *,
        project_root: Path | None,
        app_path: Path | None,
        key: str,
    ) -> object:
        if key == "persistence.backend":
            return self.describe(config, project_root=project_root, app_path=app_path).as_dict()
        root = _resolve_root(project_root=project_root, app_path=app_path)
        if root is None:
            return None
        for state_key, rel_path in _STATE_PATHS:
            if state_key != key:
                continue
            return _read_state_file(root / rel_path)
        return None

    def export_state(
        self,
        config: AppConfig,
        *,
        project_root: Path | None,
        app_path: Path | None,
    ) -> dict[str, object]:
        keys = self.list_state_keys(config, project_root=project_root, app_path=app_path)
        items: dict[str, object] = {}
        for key in keys:
            items[key] = self.inspect_state_key(config, project_root=project_root, app_path=app_path, key=key)
        return {
            "keys": keys,
            "items": items,
        }


def _resolve_root(*, project_root: Path | None, app_path: Path | None) -> Path | None:
    root = resolve_persistence_root(
        project_root=project_root,
        app_path=app_path,
        allow_create=False,
    )
    if root is None:
        return None
    return Path(root)


def _read_state_file(path: Path) -> object:
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    if path.suffix != ".json":
        return text
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"error": "invalid_json", "path": path.as_posix()}


__all__ = ["FilePersistenceBackend"]
