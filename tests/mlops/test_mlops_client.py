from __future__ import annotations

import json
from pathlib import Path

import namel3ss.mlops.client as mlops_client_module
import pytest
from namel3ss.errors.base import Namel3ssError
from namel3ss.mlops import get_mlops_client, mlops_cache_path, mlops_snapshot_path


def _write_app(tmp_path: Path) -> Path:
    app = tmp_path / "app.ai"
    app.write_text('spec is "1.0"\n\nflow "demo":\n  return "ok"\n', encoding="utf-8")
    return app


def test_register_and_get_model_snapshot_with_file_registry(tmp_path: Path) -> None:
    app = _write_app(tmp_path)
    registry_file = tmp_path / "registry_ops.json"
    (tmp_path / "mlops.yaml").write_text(
        f"registry_url: {registry_file.as_uri()}\nproject_name: demo\n",
        encoding="utf-8",
    )

    client = get_mlops_client(tmp_path, app, required=True)
    assert client is not None

    result = client.register_model(
        name="base",
        version="1.0",
        artifact_uri="model://base/1.0",
        metrics={"accuracy": 0.91, "skip": True},
        experiment_id="exp_1",
        stage="prod",
        dataset="train_set",
    )
    assert result["ok"] is True
    assert result["queued"] is False

    operations = json.loads(registry_file.read_text(encoding="utf-8"))
    assert isinstance(operations, list)
    assert len(operations) == 1
    assert operations[0]["operation"] == "register_model"

    fetched = client.get_model(name="base", version="1.0")
    assert fetched["ok"] is True
    model = fetched["model"]
    assert model["name"] == "base"
    assert model["version"] == "1.0"
    assert model["metrics"] == {"accuracy": 0.91}


def test_offline_queue_dedupes_and_replays_deterministically(tmp_path: Path, monkeypatch) -> None:
    app = _write_app(tmp_path)
    (tmp_path / "mlops.yaml").write_text(
        "registry_url: https://registry.invalid\nproject_name: demo\n",
        encoding="utf-8",
    )

    client = get_mlops_client(tmp_path, app, required=True)
    assert client is not None

    monkeypatch.setattr(mlops_client_module, "_dispatch_operation", lambda _config, _operation: False)
    first = client.register_model(
        name="candidate",
        version="2.0",
        artifact_uri="model://candidate/2.0",
        metrics={"accuracy": 0.88},
        experiment_id="exp_retry",
        stage="staging",
        dataset="feedback",
    )
    second = client.register_model(
        name="candidate",
        version="2.0",
        artifact_uri="model://candidate/2.0",
        metrics={"accuracy": 0.88},
        experiment_id="exp_retry",
        stage="staging",
        dataset="feedback",
    )
    assert first["queued"] is True
    assert second["queued"] is True

    cache = mlops_cache_path(tmp_path, app)
    assert cache is not None and cache.exists()
    queued = json.loads(cache.read_text(encoding="utf-8"))
    assert len(queued) == 1

    monkeypatch.setattr(mlops_client_module, "_dispatch_operation", lambda _config, _operation: True)
    fetched = client.get_model(name="candidate", version="2.0")
    assert fetched["ok"] is True

    queued_after = json.loads(cache.read_text(encoding="utf-8"))
    assert queued_after == []
    snapshot = mlops_snapshot_path(tmp_path, app)
    assert snapshot is not None and snapshot.exists()


def test_dispatch_operation_resolves_windows_drive_file_uri(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def _capture_write(path: Path, operation: dict[str, object], *, registry_url: str) -> None:
        captured["path"] = path
        captured["operation"] = dict(operation)
        captured["registry_url"] = registry_url

    monkeypatch.setattr(mlops_client_module, "_write_file_registry", _capture_write)
    config = mlops_client_module.MLOpsConfig(
        tool="mlflow",
        registry_url="file:///C:/Users/demo/registry_ops.json",
        project_name="demo",
        auth={},
        auth_token=None,
        training_backends=(),
    )
    operation = {"operation": "register_model", "payload": {"name": "demo"}}

    ok = mlops_client_module._dispatch_operation(config, operation)

    assert ok is True
    assert captured["registry_url"] == "file:///C:/Users/demo/registry_ops.json"
    assert isinstance(captured["path"], Path)
    assert captured["path"].as_posix() == "C:/Users/demo/registry_ops.json"


def test_dispatch_operation_rejects_malformed_file_uri() -> None:
    config = mlops_client_module.MLOpsConfig(
        tool="mlflow",
        registry_url="file:///tmp/registry_ops.json?bad=1",
        project_name="demo",
        auth={},
        auth_token=None,
        training_backends=(),
    )
    with pytest.raises(Namel3ssError):
        mlops_client_module._dispatch_operation(config, {"operation": "register_model"})
