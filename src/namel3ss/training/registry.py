from __future__ import annotations

from pathlib import Path
import re

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.models import ModelRegistryEntry, add_registry_entry, load_model_registry

_VERSION_SUFFIX = re.compile(r"(?:^|[_\-.])v?(\d+)$", re.IGNORECASE)


def ensure_output_name_available(
    *,
    project_root: Path,
    app_path: Path,
    output_name: str,
) -> None:
    registry = load_model_registry(project_root, app_path)
    for entry in registry.entries:
        if entry.name == output_name:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Model '{output_name}' already exists.",
                    why="Training does not overwrite existing registered model names.",
                    fix="Choose a new output name (for example bump the suffix).",
                    example=f"--output-name {output_name}_v2",
                )
            )


def infer_version(output_name: str) -> str:
    text = str(output_name or "").strip()
    if not text:
        return "1.0.0"
    match = _VERSION_SUFFIX.search(text)
    if match is None:
        return "1.0.0"
    try:
        major = int(match.group(1))
    except Exception:
        return "1.0.0"
    if major <= 0:
        return "1.0.0"
    return f"{major}.0.0"


def register_trained_model(
    *,
    project_root: Path,
    app_path: Path,
    output_name: str,
    version: str,
    model_base: str,
    modality: str,
    artifact_uri: str,
    dataset_snapshot: str,
    seed: int,
    created_at: str,
    metrics: dict[str, float],
    artifact_size_bytes: int,
) -> tuple[Path, ModelRegistryEntry]:
    tokens_per_second = _estimate_tokens_per_second(artifact_size_bytes)
    return add_registry_entry(
        project_root=project_root,
        app_path=app_path,
        name=output_name,
        version=version,
        provider="namel3ss",
        domain=modality,
        tokens_per_second=tokens_per_second,
        cost_per_token=0.0,
        privacy_level="internal",
        status="active",
        artifact_uri=artifact_uri,
        training_dataset_version=dataset_snapshot[:16],
        metrics=metrics,
        base_model=model_base,
        dataset_snapshot=dataset_snapshot,
        training_seed=seed,
        created_at=created_at,
    )


def _estimate_tokens_per_second(artifact_size_bytes: int) -> float:
    if artifact_size_bytes <= 0:
        return 1.0
    kb = artifact_size_bytes / 1024.0
    estimated = 150.0 / max(1.0, kb)
    return round(max(1.0, estimated), 3)


__all__ = ["ensure_output_name_available", "infer_version", "register_trained_model"]
