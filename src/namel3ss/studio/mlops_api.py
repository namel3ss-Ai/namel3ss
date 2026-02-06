from __future__ import annotations

import json
from pathlib import Path

from namel3ss.mlops import get_mlops_client, load_mlops_config, mlops_snapshot_path
from namel3ss.retrain import build_retrain_payload
from namel3ss.runtime.capabilities.feature_gate import require_app_capability


def get_mlops_payload(app_path: str) -> dict[str, object]:
    app_file = Path(app_path)
    require_app_capability(app_file, "versioning_quality_mlops")
    config = load_mlops_config(app_file.parent, app_file, required=False)
    snapshot = _read_snapshot(app_file.parent, app_file)
    return {
        "ok": True,
        "configured": config is not None,
        "config": config.to_dict() if config else None,
        "models": snapshot.get("models", []),
        "count": len(snapshot.get("models", [])),
    }


def apply_mlops_payload(source: str, body: dict, app_path: str) -> dict[str, object]:
    _ = source
    app_file = Path(app_path)
    require_app_capability(app_file, "versioning_quality_mlops", source_override=source)
    action = _text(body.get("action")) or "status"

    if action == "status":
        return get_mlops_payload(app_path)

    client = get_mlops_client(app_file.parent, app_file, required=True)
    assert client is not None

    if action == "register_model":
        payload = client.register_model(
            name=_text(body.get("name")) or "",
            version=_text(body.get("version")) or "",
            artifact_uri=_text(body.get("artifact_uri")) or "",
            metrics=_metrics(body.get("metrics")),
            experiment_id=_text(body.get("experiment_id")) or "manual",
            stage=_text(body.get("stage")) or None,
            dataset=_text(body.get("dataset")) or None,
        )
        payload["action"] = action
        return payload

    if action == "get_model":
        payload = client.get_model(
            name=_text(body.get("name")) or "",
            version=_text(body.get("version")) or "",
        )
        payload["action"] = action
        return payload

    if action == "list_models":
        payload = client.list_models()
        payload["action"] = action
        return payload

    if action == "retrain_sync":
        retrain_payload = build_retrain_payload(app_file.parent, app_file)
        payload = client.log_retrain_experiments(retrain_payload)
        payload["action"] = action
        return payload

    return {"ok": False, "error": f"Unknown action '{action}'."}


def _read_snapshot(project_root: Path, app_path: Path) -> dict[str, object]:
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


def _metrics(value: object) -> dict[str, float]:
    if not isinstance(value, dict):
        return {}
    metrics: dict[str, float] = {}
    for key in sorted(value.keys()):
        raw = value.get(key)
        if isinstance(raw, bool):
            continue
        try:
            metrics[str(key)] = float(raw)
        except Exception:
            continue
    return metrics


def _text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


__all__ = ["apply_mlops_payload", "get_mlops_payload"]
