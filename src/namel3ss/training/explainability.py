from __future__ import annotations

import hashlib
from pathlib import Path

from namel3ss.determinism import canonical_json_dump, canonical_json_dumps


def write_training_explain_report(
    *,
    model_name: str,
    version: str,
    model_base: str,
    modality: str,
    seed: int,
    dataset_snapshot: dict[str, object],
    epochs: int,
    learning_rate: float,
    validation_split: float,
    artifact_checksum: str,
    metrics: dict[str, float],
    report_dir: Path,
) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    safe_name = _safe_name(model_name)
    report_path = (report_dir / f"training_explain_{safe_name}_{version}.json").resolve()
    config_payload = {
        "model_base": model_base,
        "mode": modality,
        "epochs": int(epochs),
        "learning_rate": float(learning_rate),
        "seed": int(seed),
        "validation_split": float(validation_split),
    }
    config_hash = hashlib.sha256(
        canonical_json_dumps(config_payload, pretty=False, drop_run_keys=False).encode("utf-8")
    ).hexdigest()
    entries = [
        {
            "event_index": 1,
            "event_type": "training_start",
            "logical_timestamp": "1970-01-01T00:00:00.001Z",
            "metadata": {
                "config_hash": config_hash,
                "base_model": model_base,
                "dataset_snapshot": dict(dataset_snapshot),
                "training_seed": int(seed),
            },
        },
        {
            "event_index": 2,
            "event_type": "training_finish",
            "logical_timestamp": "1970-01-01T00:00:00.002Z",
            "metadata": {
                "version": version,
                "artifact_checksum": artifact_checksum,
                "metrics": {key: metrics[key] for key in sorted(metrics.keys())},
            },
        },
    ]
    payload = {
        "schema_version": 1,
        "model_name": model_name,
        "version": version,
        "stage": "training",
        "training_metadata": {
            "config_hash": config_hash,
            "dataset_snapshot": dict(dataset_snapshot),
            "training_seed": int(seed),
            "base_model": model_base,
            "version": version,
            "metrics": {key: metrics[key] for key in sorted(metrics.keys())},
        },
        "entries": entries,
        "entry_count": len(entries),
    }
    canonical_json_dump(report_path, payload, pretty=True, drop_run_keys=False)
    return report_path


def _safe_name(value: str) -> str:
    parts = []
    for char in str(value or ""):
        if char.isalnum() or char in {"-", "_", "."}:
            parts.append(char)
        else:
            parts.append("_")
    cleaned = "".join(parts).strip("._")
    return cleaned or "trained_model"


__all__ = ["write_training_explain_report"]
