from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Mapping

from namel3ss.determinism import canonical_json_dumps


STUDIO_WORKSPACE_SCHEMA_VERSION = "studio_workspace@1"


@dataclass(frozen=True)
class StudioWorkspaceModel:
    workspace_id: str
    app_path: str
    app_hash: str
    project_root: str

    def to_dict(self) -> dict[str, str]:
        return {
            "schema_version": STUDIO_WORKSPACE_SCHEMA_VERSION,
            "workspace_id": self.workspace_id,
            "app_path": self.app_path,
            "app_hash": self.app_hash,
            "project_root": self.project_root,
        }


def build_workspace_model(app_path: str | Path) -> StudioWorkspaceModel:
    app_file = Path(app_path).resolve()
    project_root = app_file.parent.resolve()
    app_text = _safe_read_text(app_file)
    app_hash = _sha256(app_text if app_text else app_file.as_posix())
    workspace_id = _workspace_id(app_file=app_file, app_hash=app_hash, project_root=project_root)
    return StudioWorkspaceModel(
        workspace_id=workspace_id,
        app_path=app_file.as_posix(),
        app_hash=app_hash,
        project_root=project_root.as_posix(),
    )


def workspace_storage_path(project_root: str | Path, workspace_id: str) -> Path:
    normalized_workspace_id = str(workspace_id or "").strip()
    root = Path(project_root).resolve()
    return root / ".namel3ss" / "studio" / "workspaces" / f"{normalized_workspace_id}.json"


def persist_workspace_model(model: StudioWorkspaceModel) -> Path:
    target = workspace_storage_path(model.project_root, model.workspace_id)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = model.to_dict()
    serialized = canonical_json_dumps(payload, pretty=True, drop_run_keys=False)
    if target.exists():
        existing = target.read_text(encoding="utf-8")
        if existing == serialized:
            return target
    target.write_text(serialized, encoding="utf-8")
    return target


def load_workspace_model(project_root: str | Path, workspace_id: str) -> StudioWorkspaceModel | None:
    path = workspace_storage_path(project_root, workspace_id)
    data = _read_json(path)
    if not data:
        return None
    if str(data.get("schema_version") or "").strip() != STUDIO_WORKSPACE_SCHEMA_VERSION:
        return None
    app_path = _text(data.get("app_path"))
    app_hash = _text(data.get("app_hash"))
    stored_project_root = _text(data.get("project_root"))
    if not app_path or not app_hash or not stored_project_root:
        return None
    return StudioWorkspaceModel(
        workspace_id=_text(data.get("workspace_id")) or str(workspace_id),
        app_path=app_path,
        app_hash=app_hash,
        project_root=stored_project_root,
    )


def _workspace_id(*, app_file: Path, app_hash: str, project_root: Path) -> str:
    payload = {
        "app_hash": app_hash,
        "app_path": app_file.as_posix(),
        "project_root": project_root.as_posix(),
        "schema": STUDIO_WORKSPACE_SCHEMA_VERSION,
    }
    digest = _sha256(canonical_json_dumps(payload, pretty=False, drop_run_keys=False))
    return f"workspace_{digest[:16]}"


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _safe_read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, Mapping):
        return {}
    return {str(key): data[key] for key in data.keys()}


def _text(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    return ""


__all__ = [
    "STUDIO_WORKSPACE_SCHEMA_VERSION",
    "StudioWorkspaceModel",
    "build_workspace_model",
    "load_workspace_model",
    "persist_workspace_model",
    "workspace_storage_path",
]
