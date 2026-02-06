from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import re

from namel3ss.determinism import canonical_json_dump, canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.training.config import TrainingConfig
from namel3ss.training.datasets import DatasetPartition, load_jsonl_dataset, partition_dataset
from namel3ss.training.evaluation import evaluate_validation_rows
from namel3ss.training.explainability import write_training_explain_report
from namel3ss.training.registry import ensure_output_name_available, infer_version, register_trained_model

_SANITIZE = re.compile(r"[^a-zA-Z0-9._-]+")


@dataclass(frozen=True)
class TrainingRunResult:
    model_name: str
    version: str
    model_ref: str
    artifact_path: str
    artifact_checksum: str
    registry_path: str
    report_path: str
    explain_report_path: str
    seed: int
    metrics: dict[str, float]
    dataset_snapshot: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "ok": True,
            "model_name": self.model_name,
            "version": self.version,
            "model_ref": self.model_ref,
            "artifact_path": self.artifact_path,
            "artifact_checksum": self.artifact_checksum,
            "registry_path": self.registry_path,
            "report_path": self.report_path,
            "explain_report_path": self.explain_report_path,
            "seed": self.seed,
            "metrics": {key: self.metrics[key] for key in sorted(self.metrics.keys())},
            "dataset_snapshot": dict(self.dataset_snapshot),
        }


def run_training_job(config: TrainingConfig) -> TrainingRunResult:
    ensure_output_name_available(
        project_root=config.project_root,
        app_path=config.app_path,
        output_name=config.output_name,
    )

    rows = load_jsonl_dataset(config.dataset_path)
    if len(rows) < 2:
        raise Namel3ssError(
            build_guidance_message(
                what="Dataset must contain at least 2 examples.",
                why="Training requires deterministic train/validation partitioning.",
                fix="Provide a dataset with two or more JSONL rows.",
                example='{"input":"question","target":"answer"}',
            )
        )

    partition = partition_dataset(
        path=config.dataset_path,
        rows=rows,
        seed=config.seed,
        validation_split=config.validation_split,
    )

    version = infer_version(config.output_name)
    artifact_dir = (config.output_dir / config.output_name / version).resolve()
    if artifact_dir.exists():
        raise Namel3ssError(
            build_guidance_message(
                what=f"Training artifact path already exists: {artifact_dir}",
                why="Training runs are immutable and never overwrite artifact directories.",
                fix="Use a new output model name.",
                example=f"--output-name {config.output_name}_v2",
            )
        )

    artifact_dir.mkdir(parents=True, exist_ok=False)
    metadata_payload = _build_metadata_payload(config=config, partition=partition, version=version)

    model_bytes = _build_model_bytes(metadata_payload)
    model_path = artifact_dir / "model.bin"
    model_path.write_bytes(model_bytes)
    artifact_checksum = hashlib.sha256(model_bytes).hexdigest()

    metadata_path = artifact_dir / "metadata.json"
    canonical_json_dump(metadata_path, metadata_payload, pretty=True, drop_run_keys=False)

    metrics = evaluate_validation_rows(
        modality=config.modality,
        seed=config.seed,
        artifact_checksum=artifact_checksum,
        rows=partition.validation_rows,
    )
    report_path = _write_evaluation_report(
        config=config,
        version=version,
        metrics=metrics,
        partition=partition,
        artifact_checksum=artifact_checksum,
    )
    explain_report_path = write_training_explain_report(
        model_name=config.output_name,
        version=version,
        model_base=config.model_base,
        modality=config.modality,
        seed=config.seed,
        dataset_snapshot=partition.snapshot.to_dict(),
        epochs=config.epochs,
        learning_rate=config.learning_rate,
        validation_split=config.validation_split,
        artifact_checksum=artifact_checksum,
        metrics=metrics,
        report_dir=config.report_dir,
    )

    created_at = _deterministic_created_at()
    registry_path, _entry = register_trained_model(
        project_root=config.project_root,
        app_path=config.app_path,
        output_name=config.output_name,
        version=version,
        model_base=config.model_base,
        modality=config.modality,
        artifact_uri=model_path.as_uri(),
        dataset_snapshot=partition.snapshot.content_hash,
        seed=config.seed,
        created_at=created_at,
        metrics=metrics,
        artifact_size_bytes=len(model_bytes),
    )

    return TrainingRunResult(
        model_name=config.output_name,
        version=version,
        model_ref=f"{config.output_name}@{version}",
        artifact_path=model_path.as_posix(),
        artifact_checksum=artifact_checksum,
        registry_path=registry_path.as_posix(),
        report_path=report_path.as_posix(),
        explain_report_path=explain_report_path.as_posix(),
        seed=config.seed,
        metrics={key: metrics[key] for key in sorted(metrics.keys())},
        dataset_snapshot=partition.snapshot.to_dict(),
    )


def _build_metadata_payload(
    *,
    config: TrainingConfig,
    partition: DatasetPartition,
    version: str,
) -> dict[str, object]:
    train_fingerprint = hashlib.sha256(
        canonical_json_dumps(list(partition.train_rows), pretty=False, drop_run_keys=False).encode("utf-8")
    ).hexdigest()
    validation_fingerprint = hashlib.sha256(
        canonical_json_dumps(list(partition.validation_rows), pretty=False, drop_run_keys=False).encode("utf-8")
    ).hexdigest()

    return {
        "schema_version": 1,
        "trainer": "namel3ss_deterministic",
        "model_name": config.output_name,
        "version": version,
        "model_base": config.model_base,
        "mode": config.modality,
        "epochs": config.epochs,
        "learning_rate": config.learning_rate,
        "seed": config.seed,
        "validation_split": config.validation_split,
        "dataset_snapshot": partition.snapshot.to_dict(),
        "train_count": len(partition.train_rows),
        "validation_count": len(partition.validation_rows),
        "train_fingerprint": train_fingerprint,
        "validation_fingerprint": validation_fingerprint,
    }


def _build_model_bytes(metadata_payload: dict[str, object]) -> bytes:
    stable_payload = {
        key: value
        for key, value in metadata_payload.items()
        if key not in {"model_name", "version"}
    }
    encoded = canonical_json_dumps(stable_payload, pretty=False, drop_run_keys=False).encode("utf-8")
    digest = hashlib.sha256(encoded).digest()
    # Use fixed-length deterministic artifact content.
    return digest * 32


def _write_evaluation_report(
    *,
    config: TrainingConfig,
    version: str,
    metrics: dict[str, float],
    partition: DatasetPartition,
    artifact_checksum: str,
) -> Path:
    config.report_dir.mkdir(parents=True, exist_ok=True)
    safe_name = _sanitize_name(config.output_name)
    report_path = (config.report_dir / f"training_metrics_{safe_name}_{version}.json").resolve()
    payload = {
        "schema_version": 1,
        "model_name": config.output_name,
        "version": version,
        "mode": config.modality,
        "model_base": config.model_base,
        "seed": config.seed,
        "dataset_snapshot": partition.snapshot.to_dict(),
        "train_rows": len(partition.train_rows),
        "validation_rows": len(partition.validation_rows),
        "artifact_checksum": artifact_checksum,
        "metrics": {key: metrics[key] for key in sorted(metrics.keys())},
        "measured_at": _deterministic_created_at(),
    }
    canonical_json_dump(report_path, payload, pretty=True, drop_run_keys=False)
    return report_path


def _sanitize_name(value: str) -> str:
    token = _SANITIZE.sub("_", value).strip("._")
    return token or "trained_model"


def _deterministic_created_at() -> str:
    override = os.getenv("N3_TRAIN_CREATED_AT")
    if isinstance(override, str) and override.strip():
        return override.strip()
    return "1970-01-01T00:00:00Z"


__all__ = ["TrainingRunResult", "run_training_job"]
