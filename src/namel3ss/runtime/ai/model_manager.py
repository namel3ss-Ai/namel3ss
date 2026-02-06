from __future__ import annotations

import hashlib
import subprocess
from dataclasses import dataclass
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.ai.models_config import ModelsConfig, ModelSpec, load_models_config, models_path, save_models_config
from namel3ss.runtime.tools.runners.container_detect import detect_container_runtime


@dataclass(frozen=True)
class ModelRoute:
    selected_model: str
    shadow_model: str | None
    canary_hit: bool


@dataclass(frozen=True)
class ModelManager:
    config: ModelsConfig
    runtime: str | None

    def ensure_model(self, name: str, *, project_root: str | Path | None, app_path: str | Path | None) -> None:
        spec = self.config.spec_for(name)
        if spec is None:
            raise Namel3ssError(_missing_model_message(name, project_root, app_path))
        if self.runtime is None:
            return
        _ensure_container_running(self.runtime, spec)

    def route_model(self, name: str, *, key: str, flow_name: str | None = None) -> ModelRoute:
        spec = self.config.spec_for(name)
        if spec is None:
            raise Namel3ssError(_missing_model_message(name, None, None))

        selected_model = name
        shadow_model = spec.shadow_target
        canary_hit = False

        if shadow_model and self.config.spec_for(shadow_model) is None:
            raise Namel3ssError(_missing_related_model_message(name, shadow_model, "shadow_target"))

        canary_target = spec.canary_target
        canary_fraction = float(spec.canary_fraction or 0.0)
        if canary_target and canary_fraction > 0.0:
            if self.config.spec_for(canary_target) is None:
                raise Namel3ssError(_missing_related_model_message(name, canary_target, "canary_target"))
            threshold = int(round(max(0.0, min(1.0, canary_fraction)) * 10_000))
            bucket = _bucket_for(name, flow_name or "", key)
            if bucket < threshold:
                selected_model = canary_target
                canary_hit = True
                if shadow_model is None or shadow_model == selected_model:
                    shadow_model = name

        if shadow_model == selected_model:
            shadow_model = None

        return ModelRoute(selected_model=selected_model, shadow_model=shadow_model, canary_hit=canary_hit)


def load_model_manager(project_root: str | Path | None, app_path: str | Path | None) -> ModelManager | None:
    path = models_path(project_root, app_path)
    if path is None or not path.exists():
        return None
    config = load_models_config(project_root, app_path)
    runtime = detect_container_runtime()
    return ModelManager(config=config, runtime=runtime)


def configure_canary(
    *,
    project_root: str | Path | None,
    app_path: str | Path | None,
    primary_model: str,
    candidate_model: str | None,
    fraction: float,
    shadow: bool,
) -> Path:
    if fraction < 0.0 or fraction > 1.0:
        raise Namel3ssError(
            build_guidance_message(
                what="Canary fraction is invalid.",
                why="Fraction must be a number from 0 to 1.",
                fix="Use a value like 0.1 for 10% traffic.",
                example="n3 model canary base candidate 0.1",
            )
        )
    config = load_models_config(project_root, app_path)
    primary = config.spec_for(primary_model)
    if primary is None:
        raise Namel3ssError(_missing_model_message(primary_model, project_root, app_path))
    if candidate_model:
        candidate = config.spec_for(candidate_model)
        if candidate is None:
            raise Namel3ssError(_missing_model_message(candidate_model, project_root, app_path))
    else:
        candidate_model = None

    updated = ModelSpec(
        name=primary.name,
        version=primary.version,
        image=primary.image,
        artifact_uri=primary.artifact_uri,
        stage=primary.stage,
        experiment_id=primary.experiment_id,
        cpu=primary.cpu,
        memory=primary.memory,
        canary_fraction=float(fraction) if candidate_model else None,
        canary_target=candidate_model,
        shadow_target=(candidate_model if shadow and candidate_model else None),
    )
    models = dict(config.models)
    models[primary_model] = updated
    return save_models_config(project_root, app_path, ModelsConfig(models=models))


def _ensure_container_running(runtime: str, spec: ModelSpec) -> None:
    name = _container_name(spec)
    try:
        ps = subprocess.run(
            [runtime, "ps", "--filter", f"name={name}", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            check=False,
        )
        if name in (ps.stdout or ""):
            return
        args = [runtime, "run", "-d", "--name", name]
        if spec.cpu is not None:
            args.extend(["--cpus", str(spec.cpu)])
        if spec.memory is not None:
            args.extend(["--memory", f"{spec.memory}m"])
        args.append(spec.image)
        subprocess.run(args, capture_output=True, text=True, check=False)
    except Exception:
        return


def _container_name(spec: ModelSpec) -> str:
    sanitized = spec.name.replace(" ", "_").replace("/", "_").replace(":", "_")
    return f"n3-model-{sanitized}"


def _bucket_for(model_name: str, flow_name: str, key: str) -> int:
    payload = f"{model_name}|{flow_name}|{key}".encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    return int(digest[:8], 16) % 10_000


def _missing_model_message(name: str, project_root: str | Path | None, app_path: str | Path | None) -> str:
    path = models_path(project_root, app_path)
    hint = path.as_posix() if path else "models.yaml"
    return build_guidance_message(
        what=f'Model "{name}" is not defined.',
        why="The model is not listed in models.yaml.",
        fix=f"Add the model to {hint}.",
        example='models:\n  gpt4:\n    version: "1.0"\n    image: "namel3ss/model:latest"',
    )


def _missing_related_model_message(source_name: str, target_name: str, field: str) -> str:
    return build_guidance_message(
        what=f'Model "{source_name}" has invalid {field}.',
        why=f'Referenced model "{target_name}" does not exist.',
        fix="Define the referenced model or clear the field.",
        example=(
            "models:\n"
            "  base:\n"
            "    version: \"1.0\"\n"
            "    image: \"repo/base:1\"\n"
            "    canary_target: \"candidate\"\n"
            "  candidate:\n"
            "    version: \"1.1\"\n"
            "    image: \"repo/candidate:1\""
        ),
    )


__all__ = ["ModelManager", "ModelRoute", "configure_canary", "load_model_manager"]
