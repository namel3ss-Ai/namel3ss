from __future__ import annotations

import json
from pathlib import Path

from namel3ss.determinism import canonical_json_dumps
from namel3ss.persistence.store import StoredDefinitions, merge_definitions, normalize_definitions
from namel3ss.runtime.persistence_paths import resolve_persistence_root, resolve_project_root
from namel3ss.utils.slugify import slugify_text


class LocalStore:
    def __init__(self, project_root: str | Path | None, app_path: str | Path | None) -> None:
        self._project_root = project_root
        self._app_path = app_path
        self._root = resolve_persistence_root(project_root, app_path, allow_create=True)
        if self._root is None:
            raise ValueError("Unable to resolve persistence root")
        self._project_name = _project_name(project_root, app_path)
        self._persist_root = self._root / ".namel3ss" / "persist" / self._project_name
        self._uploads_root = self._root / ".namel3ss" / "uploads" / self._project_name

    @property
    def project_name(self) -> str:
        return self._project_name

    @property
    def persist_root(self) -> Path:
        return self._persist_root

    @property
    def uploads_root(self) -> Path:
        return self._uploads_root

    def load_definitions(self) -> StoredDefinitions:
        payload = _read_json(self._definitions_path())
        return normalize_definitions(payload)

    def save_definitions(self, definitions: StoredDefinitions, *, merge_existing: bool = True) -> None:
        if merge_existing:
            existing = self.load_definitions()
            definitions = merge_definitions(existing, definitions)
        _write_json(self._definitions_path(), definitions.as_dict())

    def load_uploads(self) -> list[dict]:
        payload = _read_json(self._uploads_path())
        return _normalize_list(payload)

    def save_uploads(self, uploads: list[dict]) -> None:
        entries = [dict(entry) for entry in uploads if isinstance(entry, dict)]
        entries.sort(key=lambda item: str(item.get("upload_id") or item.get("checksum") or ""))
        _write_json(self._uploads_path(), entries)

    def load_datasets(self) -> list[dict]:
        payload = _read_json(self._datasets_path())
        return _normalize_list(payload)

    def save_datasets(self, datasets: list[dict]) -> None:
        entries = [dict(entry) for entry in datasets if isinstance(entry, dict)]
        entries.sort(key=lambda item: str(item.get("dataset_id") or item.get("name") or ""))
        _write_json(self._datasets_path(), entries)

    def upsert_upload(self, metadata: dict) -> dict:
        uploads = self.load_uploads()
        upload_id = _upload_identifier(metadata)
        uploads = [entry for entry in uploads if _upload_identifier(entry) != upload_id]
        uploads.append(dict(metadata))
        self.save_uploads(uploads)
        return metadata

    def upsert_dataset(self, entry: dict) -> dict:
        datasets = self.load_datasets()
        dataset_id = _dataset_identifier(entry)
        datasets = [item for item in datasets if _dataset_identifier(item) != dataset_id]
        datasets.append(dict(entry))
        self.save_datasets(datasets)
        return entry

    def ensure_upload_path(self) -> None:
        self._uploads_root.mkdir(parents=True, exist_ok=True)

    def upload_path_for(self, upload_id: str) -> Path:
        self.ensure_upload_path()
        return self._uploads_root / upload_id

    def _definitions_path(self) -> Path:
        return self._persist_root / "definitions.json"

    def _uploads_path(self) -> Path:
        return self._persist_root / "uploads.json"

    def _datasets_path(self) -> Path:
        return self._persist_root / "datasets.json"


def _project_name(project_root: str | Path | None, app_path: str | Path | None) -> str:
    root = resolve_project_root(project_root, app_path)
    if root:
        name = slugify_text(root.name)
        if name:
            return name
    if app_path:
        try:
            candidate = Path(app_path).stem
        except Exception:
            candidate = str(app_path)
        name = slugify_text(candidate)
        if name:
            return name
    return "app"


def _read_json(path: Path) -> object:
    try:
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_json_dumps(payload, pretty=True, drop_run_keys=False), encoding="utf-8")


def _normalize_list(payload: object) -> list[dict]:
    if not isinstance(payload, list):
        return []
    return [entry for entry in payload if isinstance(entry, dict)]


def _upload_identifier(entry: dict) -> str:
    return str(entry.get("upload_id") or entry.get("checksum") or "")


def _dataset_identifier(entry: dict) -> str:
    return str(entry.get("dataset_id") or entry.get("name") or "")


__all__ = ["LocalStore"]
