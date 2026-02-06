from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.persistence_paths import resolve_project_root
from namel3ss.utils.simple_yaml import parse_yaml, render_yaml


MODELS_DIR = ".namel3ss"
MODELS_FILE = "models.yaml"


@dataclass(frozen=True)
class ModelSpec:
    name: str
    version: str
    image: str
    artifact_uri: str | None
    stage: str | None
    experiment_id: str | None
    cpu: int | None
    memory: int | None
    canary_fraction: float | None
    canary_target: str | None
    shadow_target: str | None


@dataclass(frozen=True)
class ModelsConfig:
    models: dict[str, ModelSpec]

    def spec_for(self, name: str | None) -> ModelSpec | None:
        if not name:
            return None
        return self.models.get(name)


def models_path(project_root: str | Path | None, app_path: str | Path | None) -> Path | None:
    root = resolve_project_root(project_root, app_path)
    if root is None:
        return None
    return root / MODELS_DIR / MODELS_FILE


def load_models_config(project_root: str | Path | None, app_path: str | Path | None) -> ModelsConfig:
    path = models_path(project_root, app_path)
    if path is None or not path.exists():
        return ModelsConfig(models={})
    try:
        payload = parse_yaml(path.read_text(encoding="utf-8"))
    except Exception as err:
        raise Namel3ssError(_invalid_models_message(path)) from err
    if not isinstance(payload, dict):
        raise Namel3ssError(_invalid_models_message(path))
    values = payload.get("models")
    if values is None:
        values = payload
    if not isinstance(values, dict):
        raise Namel3ssError(_invalid_models_message(path))
    models: dict[str, ModelSpec] = {}
    for model_name, entry in values.items():
        name = str(model_name).strip()
        if not name:
            raise Namel3ssError(_invalid_models_message(path))
        models[name] = _parse_model(entry, path, name)
    return ModelsConfig(models=models)


def save_models_config(
    project_root: str | Path | None,
    app_path: str | Path | None,
    config: ModelsConfig,
) -> Path:
    path = models_path(project_root, app_path)
    if path is None:
        raise Namel3ssError("Models config path could not be resolved.")
    payload = {"models": {}}
    for name in sorted(config.models.keys()):
        model = config.models[name]
        model_payload: dict[str, object] = {
            "version": model.version,
            "image": model.image,
        }
        if model.artifact_uri:
            model_payload["artifact_uri"] = model.artifact_uri
        if model.stage:
            model_payload["stage"] = model.stage
        if model.experiment_id:
            model_payload["experiment_id"] = model.experiment_id
        if model.cpu is not None:
            model_payload["cpu"] = model.cpu
        if model.memory is not None:
            model_payload["memory"] = model.memory
        if model.canary_fraction is not None:
            model_payload["canary_fraction"] = model.canary_fraction
        if model.canary_target:
            model_payload["canary_target"] = model.canary_target
        if model.shadow_target:
            model_payload["shadow_target"] = model.shadow_target
        payload["models"][name] = model_payload
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_yaml(payload), encoding="utf-8")
    return path


def _parse_model(entry: object, path: Path, name: str) -> ModelSpec:
    if not isinstance(entry, dict):
        raise Namel3ssError(_invalid_model_message(path, name))
    version = _required_text(entry.get("version"), path, name, "version")
    image = entry.get("image")
    if not isinstance(image, str) or not image.strip():
        raise Namel3ssError(_missing_field_message(path, name, "image"))
    cpu = _optional_int(entry.get("cpu"), path, name, "cpu")
    memory = _optional_int(entry.get("memory"), path, name, "memory")
    artifact_uri = _optional_text(entry.get("artifact_uri"))
    stage = _optional_text(entry.get("stage"))
    experiment_id = _optional_text(entry.get("experiment_id"))
    canary_fraction = _optional_ratio(entry.get("canary_fraction"), path, name, "canary_fraction")
    canary_target = _optional_text(entry.get("canary_target"))
    shadow_target = _optional_text(entry.get("shadow_target"))
    return ModelSpec(
        name=name,
        version=version.strip(),
        image=image.strip(),
        artifact_uri=artifact_uri,
        stage=stage,
        experiment_id=experiment_id,
        cpu=cpu,
        memory=memory,
        canary_fraction=canary_fraction,
        canary_target=canary_target,
        shadow_target=shadow_target,
    )


def _required_text(value: object, path: Path, name: str, field: str) -> str:
    if value is None or isinstance(value, bool):
        raise Namel3ssError(_missing_field_message(path, name, field))
    if isinstance(value, str):
        text = value.strip()
        if not text:
            raise Namel3ssError(_missing_field_message(path, name, field))
        return text
    if isinstance(value, (int, float)):
        return str(value)
    raise Namel3ssError(_missing_field_message(path, name, field))


def _optional_int(value: object, path: Path, name: str, field: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise Namel3ssError(_invalid_limit_message(path, name, field))
    try:
        parsed = int(value)
    except Exception:
        raise Namel3ssError(_invalid_limit_message(path, name, field))
    if parsed <= 0:
        raise Namel3ssError(_invalid_limit_message(path, name, field))
    return parsed


def _optional_ratio(value: object, path: Path, name: str, field: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise Namel3ssError(_invalid_limit_message(path, name, field))
    try:
        parsed = float(value)
    except Exception:
        raise Namel3ssError(_invalid_limit_message(path, name, field))
    if parsed < 0.0 or parsed > 1.0:
        raise Namel3ssError(_invalid_limit_message(path, name, field))
    return parsed


def _optional_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text if text else None


def _invalid_models_message(path: Path) -> str:
    return build_guidance_message(
        what="Models config is invalid.",
        why=f"Expected a models mapping in {path.as_posix()}.",
        fix="Add models or regenerate the file.",
        example='models:\n  gpt4:\n    version: "1.0"\n    image: "namel3ss/model:latest"',
    )


def _invalid_model_message(path: Path, name: str) -> str:
    return build_guidance_message(
        what=f"Model '{name}' is invalid.",
        why=f"Expected a mapping in {path.as_posix()}.",
        fix="Provide version and image fields.",
        example='models:\n  gpt4:\n    version: "1.0"\n    image: "namel3ss/model:latest"',
    )


def _missing_field_message(path: Path, name: str, field: str) -> str:
    return build_guidance_message(
        what=f"Model '{name}' is missing {field}.",
        why=f"Each model entry needs {field} in {path.as_posix()}.",
        fix=f"Provide {field}.",
        example='models:\n  gpt4:\n    version: "1.0"\n    image: "namel3ss/model:latest"',
    )


def _invalid_limit_message(path: Path, name: str, field: str) -> str:
    if field == "canary_fraction":
        why = f"{field} must be a number from 0 to 1 in {path.as_posix()}."
        fix = f"Provide a decimal ratio for {field}."
        example = f"{field}: 0.1"
    else:
        why = f"{field} must be a positive number in {path.as_posix()}."
        fix = f"Provide a positive integer for {field}."
        example = f"{field}: 1024"
    return build_guidance_message(
        what=f"Model '{name}' has invalid {field}.",
        why=why,
        fix=fix,
        example=example,
    )


__all__ = ["ModelSpec", "ModelsConfig", "load_models_config", "save_models_config", "models_path"]
