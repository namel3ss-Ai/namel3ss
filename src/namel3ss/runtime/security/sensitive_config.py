from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.persistence_paths import resolve_project_root
from namel3ss.utils.simple_yaml import parse_yaml, render_yaml


SENSITIVE_DIR = ".namel3ss"
SENSITIVE_FILE = "sensitive.yaml"


@dataclass(frozen=True)
class SensitiveConfig:
    flows: dict[str, bool]

    def is_sensitive(self, flow_name: str | None) -> bool:
        if not flow_name:
            return False
        return bool(self.flows.get(flow_name, False))


def sensitive_path(project_root: str | Path | None, app_path: str | Path | None) -> Path | None:
    root = resolve_project_root(project_root, app_path)
    if root is None:
        return None
    return root / SENSITIVE_DIR / SENSITIVE_FILE


def load_sensitive_config(project_root: str | Path | None, app_path: str | Path | None) -> SensitiveConfig:
    path = sensitive_path(project_root, app_path)
    if path is None or not path.exists():
        return SensitiveConfig(flows={})
    try:
        payload = parse_yaml(path.read_text(encoding="utf-8"))
    except Exception as err:
        raise Namel3ssError(_invalid_sensitive_message(path)) from err
    if not isinstance(payload, dict):
        raise Namel3ssError(_invalid_sensitive_message(path))
    values = payload.get("sensitive")
    if values is None:
        values = payload
    if not isinstance(values, dict):
        raise Namel3ssError(_invalid_sensitive_message(path))
    flows: dict[str, bool] = {}
    for key, value in values.items():
        name = str(key).strip()
        if not name:
            raise Namel3ssError(_invalid_sensitive_message(path))
        if isinstance(value, bool):
            flows[name] = value
        elif value is None:
            flows[name] = True
        else:
            raise Namel3ssError(_invalid_sensitive_value_message(path, name))
    return SensitiveConfig(flows=flows)


def save_sensitive_config(
    project_root: str | Path | None,
    app_path: str | Path | None,
    config: SensitiveConfig,
) -> Path:
    path = sensitive_path(project_root, app_path)
    if path is None:
        raise Namel3ssError("Sensitive config path could not be resolved.")
    payload = {"sensitive": {name: True for name, value in sorted(config.flows.items()) if value}}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_yaml(payload), encoding="utf-8")
    return path


def _invalid_sensitive_message(path: Path) -> str:
    return build_guidance_message(
        what="Sensitive config is invalid.",
        why=f"Expected a sensitive mapping in {path.as_posix()}.",
        fix="Regenerate the file with n3 sensitive add or edit it to match the expected shape.",
        example="sensitive:\n  process_order: true",
    )


def _invalid_sensitive_value_message(path: Path, name: str) -> str:
    return build_guidance_message(
        what=f"Sensitive flag for '{name}' is invalid.",
        why=f"Sensitive values must be true or false in {path.as_posix()}.",
        fix="Set the flow to true or remove the entry.",
        example="sensitive:\n  process_order: true",
    )


__all__ = ["SensitiveConfig", "load_sensitive_config", "save_sensitive_config", "sensitive_path"]
