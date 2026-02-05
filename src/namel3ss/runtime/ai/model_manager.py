from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.ai.models_config import ModelsConfig, ModelSpec, load_models_config, models_path
from namel3ss.runtime.tools.runners.container_detect import detect_container_runtime


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


def load_model_manager(project_root: str | Path | None, app_path: str | Path | None) -> ModelManager | None:
    path = models_path(project_root, app_path)
    if path is None or not path.exists():
        return None
    config = load_models_config(project_root, app_path)
    runtime = detect_container_runtime()
    return ModelManager(config=config, runtime=runtime)


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


def _missing_model_message(name: str, project_root: str | Path | None, app_path: str | Path | None) -> str:
    path = models_path(project_root, app_path)
    hint = path.as_posix() if path else "models.yaml"
    return build_guidance_message(
        what=f'Model "{name}" is not defined.',
        why="The model is not listed in models.yaml.",
        fix=f"Add the model to {hint}.",
        example='models:\n  gpt4:\n    version: "1.0"\n    image: "namel3ss/model:latest"',
    )


__all__ = ["ModelManager", "load_model_manager"]
