from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Mapping

from namel3ss.config.model import AppConfig
from namel3ss.runtime.audit.audit_bundle import load_run_artifact
from namel3ss.runtime.storage.base import Storage
from namel3ss.runtime.storage.factory import create_store
from namel3ss.runtime.memory.api import MemoryManager
from namel3ss.determinism import canonical_json_dumps
from namel3ss.studio.diff.run_diff import build_run_diff
from namel3ss.studio.share.repro_bundle import (
    build_repro_bundle,
    load_repro_bundle,
    write_repro_bundle,
)
from namel3ss.studio.workspace.workspace_model import (
    StudioWorkspaceModel,
    build_workspace_model,
    persist_workspace_model,
)


STUDIO_SESSION_SCHEMA_VERSION = "studio_session@1"


@dataclass(frozen=True)
class StudioSessionModel:
    session_id: str
    workspace_id: str
    run_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": STUDIO_SESSION_SCHEMA_VERSION,
            "session_id": self.session_id,
            "workspace_id": self.workspace_id,
            "run_ids": list(self.run_ids),
        }


@dataclass
class SessionState:
    state: dict = field(default_factory=dict)
    store: Storage | None = None
    runtime_theme: str | None = None
    memory_manager: MemoryManager | None = None
    data_effects: dict | None = None
    last_answer_explain: dict | None = None
    runtime_errors: list[dict[str, str]] = field(default_factory=list)
    workspace: StudioWorkspaceModel | None = None
    studio_session: StudioSessionModel | None = None
    last_run_artifact: dict | None = None
    last_run_diff: dict | None = None
    last_repro_bundle: dict | None = None

    def ensure_store(self, config: AppConfig | None = None) -> Storage:
        if self.store is None:
            self.store = create_store(config=config)
        return self.store

    def attach_workspace(self, app_path: str | Path) -> None:
        workspace = build_workspace_model(app_path)
        persist_workspace_model(workspace)
        session = load_session_model(workspace)
        if session is None:
            session = build_session_model(workspace)
            persist_session_model(workspace, session)
        self.workspace = workspace
        self.studio_session = session
        if session.run_ids:
            latest = session.run_ids[-1]
            artifact = load_run_artifact(workspace.project_root, run_id=latest)
            if artifact:
                self.last_run_artifact = artifact
            repro_bundle = load_repro_bundle(workspace.project_root, run_id=latest)
            if repro_bundle:
                self.last_repro_bundle = repro_bundle
            if len(session.run_ids) > 1 and artifact:
                previous = load_run_artifact(workspace.project_root, run_id=session.run_ids[-2])
                self.last_run_diff = build_run_diff(previous or {}, artifact)

    def record_run_artifact(self, run_artifact: Mapping[str, object]) -> None:
        workspace = self.workspace
        studio_session = self.studio_session
        if workspace is None or studio_session is None:
            return
        artifact = _mapping_or_empty(run_artifact)
        run_id = _text(artifact.get("run_id"))
        if not run_id:
            return
        previous_run_id = studio_session.run_ids[-1] if studio_session.run_ids else ""
        updated_session = append_run_id(workspace, studio_session, run_id)
        self.studio_session = updated_session
        self.last_run_artifact = artifact
        if previous_run_id and previous_run_id != run_id:
            previous = load_run_artifact(workspace.project_root, run_id=previous_run_id)
            self.last_run_diff = build_run_diff(previous or {}, artifact)
        elif not self.last_run_diff:
            self.last_run_diff = build_run_diff({}, artifact)
        repro_bundle = build_repro_bundle(
            run_artifact=artifact,
            workspace_id=workspace.workspace_id,
            session_id=updated_session.session_id,
        )
        write_repro_bundle(workspace.project_root, repro_bundle)
        self.last_repro_bundle = repro_bundle

    def run_history(self) -> list[str]:
        if self.studio_session is None:
            return []
        return list(self.studio_session.run_ids)


def build_session_model(workspace: StudioWorkspaceModel) -> StudioSessionModel:
    digest = _sha256(
        canonical_json_dumps(
            {"schema": STUDIO_SESSION_SCHEMA_VERSION, "workspace_id": workspace.workspace_id},
            pretty=False,
            drop_run_keys=False,
        )
    )
    session_id = f"session_{digest[:16]}"
    return StudioSessionModel(
        session_id=session_id,
        workspace_id=workspace.workspace_id,
        run_ids=(),
    )


def append_run_id(
    workspace: StudioWorkspaceModel,
    model: StudioSessionModel,
    run_id: str,
) -> StudioSessionModel:
    text_run_id = _text(run_id)
    if not text_run_id:
        persist_session_model(workspace, model)
        return model
    ordered: list[str] = [entry for entry in model.run_ids if entry != text_run_id]
    ordered.append(text_run_id)
    updated = StudioSessionModel(
        session_id=model.session_id,
        workspace_id=model.workspace_id,
        run_ids=tuple(ordered),
    )
    persist_session_model(workspace, updated)
    return updated


def session_storage_path(project_root: str | Path, workspace_id: str) -> Path:
    normalized_workspace_id = str(workspace_id or "").strip()
    root = Path(project_root).resolve()
    return root / ".namel3ss" / "studio" / "sessions" / f"{normalized_workspace_id}.json"


def persist_session_model(workspace: StudioWorkspaceModel, model: StudioSessionModel) -> Path:
    target = session_storage_path(workspace.project_root, workspace.workspace_id)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = model.to_dict()
    serialized = canonical_json_dumps(payload, pretty=True, drop_run_keys=False)
    if target.exists():
        existing = target.read_text(encoding="utf-8")
        if existing == serialized:
            return target
    target.write_text(serialized, encoding="utf-8")
    return target


def load_session_model(workspace: StudioWorkspaceModel) -> StudioSessionModel | None:
    path = session_storage_path(workspace.project_root, workspace.workspace_id)
    data = _read_json(path)
    if not data:
        return None
    if _text(data.get("schema_version")) != STUDIO_SESSION_SCHEMA_VERSION:
        return None
    session_id = _text(data.get("session_id"))
    workspace_id = _text(data.get("workspace_id"))
    if workspace_id != workspace.workspace_id:
        return None
    run_ids = tuple(_normalize_run_ids(data.get("run_ids")))
    if not session_id:
        return None
    return StudioSessionModel(
        session_id=session_id,
        workspace_id=workspace_id,
        run_ids=run_ids,
    )


def _normalize_run_ids(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    seen: set[str] = set()
    ordered: list[str] = []
    for item in value:
        run_id = _text(item)
        if not run_id or run_id in seen:
            continue
        seen.add(run_id)
        ordered.append(run_id)
    return ordered


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


def _mapping_or_empty(value: object) -> dict[str, object]:
    if isinstance(value, Mapping):
        return {str(key): value[key] for key in value.keys()}
    return {}


def _text(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    return ""


def _sha256(value: str) -> str:
    import hashlib

    return hashlib.sha256(value.encode("utf-8")).hexdigest()


__all__ = [
    "STUDIO_SESSION_SCHEMA_VERSION",
    "SessionState",
    "StudioSessionModel",
    "append_run_id",
    "build_session_model",
    "load_session_model",
    "persist_session_model",
    "session_storage_path",
]
