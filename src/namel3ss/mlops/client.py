from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from namel3ss.determinism import canonical_json_dump, canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.mlops.config_helpers import (
    auth_header_for_config,
    normalize_auth_map,
    normalize_tool_name,
    normalize_training_backends,
)
from namel3ss.runtime.persistence_paths import resolve_persistence_root, resolve_project_root
from namel3ss.utils.simple_yaml import parse_yaml


MLOPS_FILENAME = "mlops.yaml"
MLOPS_CACHE_FILENAME = "mlops_cache.json"
MLOPS_SNAPSHOT_FILENAME = "mlops_registry.json"


@dataclass(frozen=True)
class MLOpsConfig:
    tool: str
    registry_url: str
    project_name: str
    auth: dict[str, str]
    auth_token: str | None
    training_backends: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "tool": self.tool,
            "registry_url": self.registry_url,
            "project_name": self.project_name,
        }
        if self.auth:
            payload["auth"] = {key: self.auth[key] for key in sorted(self.auth.keys())}
        if self.auth_token:
            payload["auth_token"] = self.auth_token
        if self.training_backends:
            payload["training_backends"] = list(self.training_backends)
        return payload


@dataclass(frozen=True)
class ModelRegistryEntry:
    name: str
    version: str
    artifact_uri: str
    metrics: dict[str, float]
    experiment_id: str
    stage: str | None
    dataset: str | None

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "name": self.name,
            "version": self.version,
            "artifact_uri": self.artifact_uri,
            "metrics": {key: float(self.metrics[key]) for key in sorted(self.metrics.keys())},
            "experiment_id": self.experiment_id,
        }
        if self.stage:
            payload["stage"] = self.stage
        if self.dataset:
            payload["dataset"] = self.dataset
        payload["entry_id"] = _entry_id(self.name, self.version, self.artifact_uri)
        return payload


def mlops_config_path(project_root: str | Path | None, app_path: str | Path | None) -> Path | None:
    root = resolve_project_root(project_root, app_path)
    if root is None:
        return None
    return Path(root) / MLOPS_FILENAME


def load_mlops_config(
    project_root: str | Path | None,
    app_path: str | Path | None,
    *,
    required: bool = False,
) -> MLOpsConfig | None:
    path = mlops_config_path(project_root, app_path)
    if path is None or not path.exists():
        if required:
            raise Namel3ssError(_missing_config_message())
        return None
    try:
        payload = parse_yaml(path.read_text(encoding="utf-8"))
    except Exception as err:
        raise Namel3ssError(_invalid_config_message(path, str(err))) from err
    if not isinstance(payload, dict):
        raise Namel3ssError(_invalid_config_message(path, "expected YAML mapping"))
    tool = normalize_tool_name(payload.get("tool"))
    registry_url = str(payload.get("registry_url") or "").strip()
    project_name = str(payload.get("project_name") or "").strip()
    auth = normalize_auth_map(payload.get("auth"))
    training_backends = normalize_training_backends(payload.get("training_backends"))
    auth_token = payload.get("auth_token")
    token = _optional_text(auth_token)
    if not token and "token" in auth:
        token = auth["token"]
    if not registry_url or not project_name:
        raise Namel3ssError(_invalid_config_message(path, "registry_url and project_name are required"))
    return MLOpsConfig(
        tool=tool,
        registry_url=registry_url,
        project_name=project_name,
        auth=auth,
        auth_token=token,
        training_backends=training_backends,
    )


def mlops_cache_path(project_root: str | Path | None, app_path: str | Path | None) -> Path | None:
    root = resolve_persistence_root(project_root, app_path)
    if root is None:
        return None
    return Path(root) / ".namel3ss" / MLOPS_CACHE_FILENAME


def mlops_snapshot_path(project_root: str | Path | None, app_path: str | Path | None) -> Path | None:
    root = resolve_persistence_root(project_root, app_path)
    if root is None:
        return None
    return Path(root) / ".namel3ss" / MLOPS_SNAPSHOT_FILENAME


class MLOpsClient:
    def __init__(self, project_root: str | Path | None, app_path: str | Path | None, config: MLOpsConfig) -> None:
        self.project_root = project_root
        self.app_path = app_path
        self.config = config

    def register_model(
        self,
        *,
        name: str,
        version: str,
        artifact_uri: str,
        metrics: dict[str, float] | None,
        experiment_id: str,
        stage: str | None,
        dataset: str | None,
    ) -> dict[str, object]:
        entry = ModelRegistryEntry(
            name=_text(name, "name"),
            version=_text(version, "version"),
            artifact_uri=_text(artifact_uri, "artifact_uri"),
            metrics=_normalize_metrics(metrics or {}),
            experiment_id=_text(experiment_id, "experiment_id"),
            stage=_optional_text(stage),
            dataset=_optional_text(dataset),
        )
        payload = entry.to_dict()
        _save_model_snapshot(self.project_root, self.app_path, payload)

        operation = {
            "operation": "register_model",
            "payload": payload,
            "project": self.config.project_name,
            "registry": self.config.registry_url,
        }
        queued = False
        if not _dispatch_operation(self.config, operation):
            _queue_operation(self.project_root, self.app_path, operation)
            queued = True
        else:
            _sync_cached_operations(self.project_root, self.app_path, self.config)

        return {
            "ok": True,
            "queued": queued,
            "model": payload,
        }

    def get_model(self, *, name: str, version: str) -> dict[str, object]:
        normalized_name = _text(name, "name")
        normalized_version = _text(version, "version")
        _sync_cached_operations(self.project_root, self.app_path, self.config)
        record = _find_model_snapshot(self.project_root, self.app_path, normalized_name, normalized_version)
        if record is None:
            return {
                "ok": False,
                "error": f"Model {normalized_name}@{normalized_version} not found.",
            }
        return {
            "ok": True,
            "model": record,
        }

    def list_models(self) -> dict[str, object]:
        _sync_cached_operations(self.project_root, self.app_path, self.config)
        payload = _snapshot_payload(self.project_root, self.app_path)
        models = [item for item in payload.get("models", []) if isinstance(item, dict)]
        ordered = sorted(models, key=lambda item: _entry_key(str(item.get("name") or ""), str(item.get("version") or "")))
        return {"ok": True, "count": len(ordered), "models": ordered}

    def log_retrain_experiments(self, retrain_payload: dict[str, object]) -> dict[str, object]:
        suggestions = retrain_payload.get("suggestions")
        if not isinstance(suggestions, list) or not suggestions:
            return {"ok": True, "count": 0, "queued": 0}

        metrics = retrain_payload.get("metrics")
        feedback_metrics = {}
        if isinstance(metrics, dict):
            feedback = metrics.get("feedback")
            if isinstance(feedback, dict):
                for key, value in feedback.items():
                    try:
                        feedback_metrics[str(key)] = float(value)
                    except Exception:
                        continue

        total = 0
        queued = 0
        for suggestion in suggestions:
            if not isinstance(suggestion, dict):
                continue
            model_name = str(suggestion.get("model_name") or "").strip() or "default"
            reason = str(suggestion.get("reason") or "retrain_suggestion")
            experiment_id = _experiment_id(model_name, reason)
            register_payload = {
                "name": model_name,
                "version": "retrain-suggested",
                "artifact_uri": f"pending://{model_name}/{experiment_id}",
                "metrics": feedback_metrics,
                "experiment_id": experiment_id,
                "stage": "suggested",
                "dataset": "feedback",
            }
            operation = {
                "operation": "register_model",
                "payload": register_payload,
                "project": self.config.project_name,
                "registry": self.config.registry_url,
            }
            _save_model_snapshot(self.project_root, self.app_path, register_payload)
            total += 1
            if not _dispatch_operation(self.config, operation):
                _queue_operation(self.project_root, self.app_path, operation)
                queued += 1
        if queued < total:
            _sync_cached_operations(self.project_root, self.app_path, self.config)
        return {"ok": True, "count": total, "queued": queued}


def get_mlops_client(
    project_root: str | Path | None,
    app_path: str | Path | None,
    *,
    required: bool = False,
) -> MLOpsClient | None:
    config = load_mlops_config(project_root, app_path, required=required)
    if config is None:
        return None
    return MLOpsClient(project_root, app_path, config)


def _dispatch_operation(config: MLOpsConfig, operation: dict[str, object]) -> bool:
    url = config.registry_url
    parsed = urlparse(url)
    if parsed.scheme in {"", "file"}:
        target = Path(parsed.path if parsed.scheme == "file" else url).expanduser()
        _write_file_registry(target, operation)
        return True
    if parsed.scheme in {"http", "https"}:
        return _dispatch_http(config, operation)
    return False


def _dispatch_http(config: MLOpsConfig, operation: dict[str, object]) -> bool:
    payload = canonical_json_dumps(operation, pretty=False, drop_run_keys=False).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    auth_header = auth_header_for_config(auth_token=config.auth_token, auth=config.auth)
    if auth_header:
        headers["Authorization"] = auth_header
    request = Request(config.registry_url.rstrip("/") + "/ops", data=payload, headers=headers, method="POST")
    try:
        with urlopen(request, timeout=2):
            return True
    except URLError:
        return False
    except Exception:
        return False


def _write_file_registry(path: Path, operation: dict[str, object]) -> None:
    existing = []
    if path.exists():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, list):
                existing = [item for item in payload if isinstance(item, dict)]
        except Exception:
            existing = []
    existing.append(operation)
    existing = sorted(existing, key=lambda item: _operation_id(item))
    path.parent.mkdir(parents=True, exist_ok=True)
    canonical_json_dump(path, existing, pretty=True, drop_run_keys=False)


def _queue_operation(project_root: str | Path | None, app_path: str | Path | None, operation: dict[str, object]) -> None:
    path = mlops_cache_path(project_root, app_path)
    if path is None:
        return
    queued = _load_operations(path)
    queued.append(operation)
    queued = _dedupe_operations(queued)
    path.parent.mkdir(parents=True, exist_ok=True)
    canonical_json_dump(path, queued, pretty=True, drop_run_keys=False)


def _sync_cached_operations(project_root: str | Path | None, app_path: str | Path | None, config: MLOpsConfig) -> None:
    path = mlops_cache_path(project_root, app_path)
    if path is None or not path.exists():
        return
    queued = _load_operations(path)
    if not queued:
        return
    pending: list[dict[str, object]] = []
    for operation in queued:
        if not _dispatch_operation(config, operation):
            pending.append(operation)
    pending = _dedupe_operations(pending)
    canonical_json_dump(path, pending, pretty=True, drop_run_keys=False)


def _load_operations(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict)]


def _dedupe_operations(values: list[dict[str, object]]) -> list[dict[str, object]]:
    unique: dict[str, dict[str, object]] = {}
    for item in values:
        unique[_operation_id(item)] = item
    return [unique[key] for key in sorted(unique.keys())]


def _operation_id(operation: dict[str, object]) -> str:
    text = canonical_json_dumps(operation, pretty=False, drop_run_keys=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _snapshot_payload(project_root: str | Path | None, app_path: str | Path | None) -> dict[str, object]:
    path = mlops_snapshot_path(project_root, app_path)
    if path is None or not path.exists():
        return {"schema_version": 1, "models": []}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"schema_version": 1, "models": []}
    if not isinstance(payload, dict):
        return {"schema_version": 1, "models": []}
    models = payload.get("models")
    if not isinstance(models, list):
        payload["models"] = []
    return payload


def _save_model_snapshot(project_root: str | Path | None, app_path: str | Path | None, entry: dict[str, object]) -> None:
    path = mlops_snapshot_path(project_root, app_path)
    if path is None:
        return
    payload = _snapshot_payload(project_root, app_path)
    models = [item for item in payload.get("models", []) if isinstance(item, dict)]
    key = _entry_key(str(entry.get("name") or ""), str(entry.get("version") or ""))
    deduped: dict[str, dict[str, object]] = {}
    for item in models:
        deduped[_entry_key(str(item.get("name") or ""), str(item.get("version") or ""))] = item
    deduped[key] = {
        **entry,
        "metrics": _normalize_metrics(entry.get("metrics") if isinstance(entry.get("metrics"), dict) else {}),
    }
    ordered = [deduped[key_name] for key_name in sorted(deduped.keys())]
    payload["models"] = ordered
    path.parent.mkdir(parents=True, exist_ok=True)
    canonical_json_dump(path, payload, pretty=True, drop_run_keys=False)


def _find_model_snapshot(
    project_root: str | Path | None,
    app_path: str | Path | None,
    name: str,
    version: str,
) -> dict[str, object] | None:
    payload = _snapshot_payload(project_root, app_path)
    models = payload.get("models")
    if not isinstance(models, list):
        return None
    for item in models:
        if not isinstance(item, dict):
            continue
        if str(item.get("name") or "") == name and str(item.get("version") or "") == version:
            return item
    return None


def _normalize_metrics(raw: dict[str, object] | dict[str, float]) -> dict[str, float]:
    metrics: dict[str, float] = {}
    for key in sorted(raw.keys()):
        value = raw[key]
        if isinstance(value, bool):
            continue
        try:
            metrics[str(key)] = float(value)
        except Exception:
            continue
    return metrics


def _entry_key(name: str, version: str) -> str:
    return f"{name}@{version}"


def _entry_id(name: str, version: str, artifact_uri: str) -> str:
    payload = f"{name}|{version}|{artifact_uri}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


def _experiment_id(model_name: str, reason: str) -> str:
    payload = f"{model_name}|{reason}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:12]


def _text(value: object, field: str) -> str:
    text = str(value or "").strip()
    if text:
        return text
    raise Namel3ssError(
        build_guidance_message(
            what=f"{field} is required.",
            why=f"MLOps operations require {field}.",
            fix=f"Provide {field} and retry.",
            example="n3 mlops register-model base 1.0 --artifact-uri model://base/1.0",
        )
    )


def _optional_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text if text else None


def _missing_config_message() -> str:
    return build_guidance_message(
        what="mlops.yaml is missing.",
        why="MLOps commands need tool, registry_url, and project_name.",
        fix="Create mlops.yaml at project root.",
        example="tool: mlflow\nregistry_url: file://./registry.json\nproject_name: demo",
    )


def _invalid_config_message(path: Path, details: str) -> str:
    return build_guidance_message(
        what="mlops.yaml is invalid.",
        why=f"{path.as_posix()} could not be parsed: {details}.",
        fix="Set tool, registry_url, and project_name.",
        example="tool: mlflow\nregistry_url: file://./registry.json\nproject_name: demo",
    )


__all__ = [
    "MLOPS_CACHE_FILENAME",
    "MLOPS_FILENAME",
    "MLOPS_SNAPSHOT_FILENAME",
    "MLOpsClient",
    "MLOpsConfig",
    "ModelRegistryEntry",
    "get_mlops_client",
    "load_mlops_config",
    "mlops_cache_path",
    "mlops_config_path",
    "mlops_snapshot_path",
]
