from __future__ import annotations

from pathlib import Path

from namel3ss.compilation.model import CompilationConfig, SUPPORTED_TARGETS
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.persistence_paths import resolve_project_root
from namel3ss.utils.simple_yaml import parse_yaml, render_yaml


COMPILATION_FILENAME = "compilation.yaml"


def compilation_path(project_root: str | Path | None, app_path: str | Path | None) -> Path | None:
    root = resolve_project_root(project_root, app_path)
    if root is None:
        return None
    return Path(root) / COMPILATION_FILENAME


def load_compilation_config(project_root: str | Path | None, app_path: str | Path | None) -> CompilationConfig:
    path = compilation_path(project_root, app_path)
    if path is None or not path.exists():
        return CompilationConfig(flows={})
    try:
        payload = parse_yaml(path.read_text(encoding="utf-8"))
    except Exception as err:
        raise Namel3ssError(_invalid_file_message(path, str(err))) from err
    if not isinstance(payload, dict):
        raise Namel3ssError(_invalid_file_message(path, "expected YAML mapping"))
    raw_flows = payload.get("flows")
    if raw_flows is None:
        return CompilationConfig(flows={})
    if not isinstance(raw_flows, dict):
        raise Namel3ssError(_invalid_file_message(path, "flows must be a map of flow name to target"))
    flows: dict[str, str] = {}
    for key in sorted(raw_flows.keys(), key=str):
        name = _normalize_flow_name(key)
        target = _normalize_target(raw_flows.get(key))
        flows[name] = target
    return CompilationConfig(flows=flows)


def save_compilation_config(
    project_root: str | Path | None,
    app_path: str | Path | None,
    config: CompilationConfig,
) -> Path:
    path = compilation_path(project_root, app_path)
    if path is None:
        raise Namel3ssError(_missing_path_message())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_yaml(config.to_dict()), encoding="utf-8")
    return path


def _normalize_flow_name(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        raise Namel3ssError(
            build_guidance_message(
                what="Flow name is missing in compilation.yaml.",
                why="Each flows entry needs a non-empty name.",
                fix="Use flow names as keys under flows.",
                example="flows:\n  add: wasm",
            )
        )
    return text


def _normalize_target(value: object) -> str:
    text = str(value or "").strip().lower()
    if text in SUPPORTED_TARGETS:
        return text
    joined = ", ".join(SUPPORTED_TARGETS)
    raise Namel3ssError(
        build_guidance_message(
            what=f"Unknown compilation target '{text or '<empty>'}'.",
            why=f"Supported targets are: {joined}.",
            fix="Set each flow target to c, rust, or wasm.",
            example="flows:\n  add: rust",
        )
    )


def _missing_path_message() -> str:
    return build_guidance_message(
        what="Compilation config path could not be resolved.",
        why="Project root is required to read or write compilation.yaml.",
        fix="Run this command from a project with app.ai.",
        example="n3 compile list",
    )


def _invalid_file_message(path: Path, details: str) -> str:
    return build_guidance_message(
        what="compilation.yaml is invalid.",
        why=f"{path.as_posix()} could not be parsed: {details}.",
        fix="Fix compilation.yaml and try again.",
        example="flows:\n  add: wasm",
    )


__all__ = [
    "COMPILATION_FILENAME",
    "compilation_path",
    "load_compilation_config",
    "save_compilation_config",
]
