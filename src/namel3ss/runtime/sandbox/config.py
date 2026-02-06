from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.persistence_paths import resolve_project_root
from namel3ss.utils.simple_yaml import parse_yaml, render_yaml


SANDBOX_DIR = ".namel3ss"
SANDBOX_FILE = "sandbox.yaml"


@dataclass(frozen=True)
class SandboxFlow:
    entry: str | None
    command: str | None
    image: str | None
    cpu_seconds: int | None
    memory_mb: int | None
    timeout_seconds: int | None
    allow_network: bool


@dataclass(frozen=True)
class SandboxConfig:
    flows: dict[str, SandboxFlow]

    def flow_for(self, name: str | None) -> SandboxFlow | None:
        if not name:
            return None
        return self.flows.get(name)


def sandbox_path(project_root: str | Path | None, app_path: str | Path | None) -> Path | None:
    root = resolve_project_root(project_root, app_path)
    if root is None:
        return None
    return root / SANDBOX_DIR / SANDBOX_FILE


def load_sandbox_config(project_root: str | Path | None, app_path: str | Path | None) -> SandboxConfig:
    path = sandbox_path(project_root, app_path)
    if path is None or not path.exists():
        return SandboxConfig(flows={})
    try:
        payload = parse_yaml(path.read_text(encoding="utf-8"))
    except Exception as err:
        raise Namel3ssError(_invalid_sandbox_message(path)) from err
    if not isinstance(payload, dict):
        raise Namel3ssError(_invalid_sandbox_message(path))
    values = payload.get("sandboxes")
    if values is None:
        values = payload.get("flows", payload)
    if not isinstance(values, dict):
        raise Namel3ssError(_invalid_sandbox_message(path))
    flows: dict[str, SandboxFlow] = {}
    for flow_name, entry in values.items():
        name = str(flow_name).strip()
        if not name:
            raise Namel3ssError(_invalid_sandbox_message(path))
        flow = _parse_flow(entry, path, name)
        flows[name] = flow
    return SandboxConfig(flows=flows)


def save_sandbox_config(
    project_root: str | Path | None,
    app_path: str | Path | None,
    config: SandboxConfig,
) -> Path:
    path = sandbox_path(project_root, app_path)
    if path is None:
        raise Namel3ssError("Sandbox config path could not be resolved.")
    payload = {"sandboxes": {}}
    for name in sorted(config.flows.keys()):
        flow = config.flows[name]
        flow_payload: dict[str, object] = {
            "allow_network": bool(flow.allow_network),
        }
        if flow.entry is not None:
            flow_payload["entry"] = flow.entry
        if flow.command is not None:
            flow_payload["command"] = flow.command
        if flow.image is not None:
            flow_payload["image"] = flow.image
        if flow.cpu_seconds is not None:
            flow_payload["cpu_seconds"] = flow.cpu_seconds
        if flow.memory_mb is not None:
            flow_payload["memory_mb"] = flow.memory_mb
        if flow.timeout_seconds is not None:
            flow_payload["timeout_seconds"] = flow.timeout_seconds
        payload["sandboxes"][name] = flow_payload
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_yaml(payload), encoding="utf-8")
    return path


def _parse_flow(entry: object, path: Path, flow_name: str) -> SandboxFlow:
    if not isinstance(entry, dict):
        raise Namel3ssError(_invalid_flow_message(path, flow_name))
    entry_value = entry.get("entry")
    command_value = entry.get("command")
    if entry_value is not None and (not isinstance(entry_value, str) or not entry_value.strip()):
        raise Namel3ssError(_invalid_field_message(path, flow_name, "entry"))
    if command_value is not None and (not isinstance(command_value, str) or not command_value.strip()):
        raise Namel3ssError(_invalid_field_message(path, flow_name, "command"))
    entry_value = entry_value.strip() if isinstance(entry_value, str) else None
    command_value = command_value.strip() if isinstance(command_value, str) else None
    if not entry_value and not command_value:
        raise Namel3ssError(_missing_entry_message(path, flow_name))
    image = entry.get("image")
    if image is not None and (not isinstance(image, str) or not image.strip()):
        raise Namel3ssError(_invalid_field_message(path, flow_name, "image"))
    cpu_seconds = _optional_int(entry.get("cpu_seconds"), path, flow_name, "cpu_seconds")
    memory_mb = _optional_int(entry.get("memory_mb"), path, flow_name, "memory_mb")
    timeout_seconds = _optional_int(entry.get("timeout_seconds"), path, flow_name, "timeout_seconds")
    allow_network = bool(entry.get("allow_network")) if "allow_network" in entry else False
    return SandboxFlow(
        entry=entry_value,
        command=command_value,
        image=str(image).strip() if isinstance(image, str) else None,
        cpu_seconds=cpu_seconds,
        memory_mb=memory_mb,
        timeout_seconds=timeout_seconds,
        allow_network=allow_network,
    )


def _optional_int(value: object, path: Path, flow_name: str, field: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise Namel3ssError(_invalid_limit_message(path, flow_name, field))
    try:
        parsed = int(value)
    except Exception:
        raise Namel3ssError(_invalid_limit_message(path, flow_name, field))
    if parsed <= 0:
        raise Namel3ssError(_invalid_limit_message(path, flow_name, field))
    return parsed


def _invalid_sandbox_message(path: Path) -> str:
    return build_guidance_message(
        what="Sandbox config is invalid.",
        why=f"Expected a sandboxes mapping in {path.as_posix()}.",
        fix="Regenerate the file with n3 sandbox configure or edit it to match the expected shape.",
        example='sandboxes:\n  summarize:\n    entry: "plugins.summarize:run"',
    )


def _invalid_flow_message(path: Path, flow_name: str) -> str:
    return build_guidance_message(
        what=f"Sandbox entry for '{flow_name}' is invalid.",
        why=f"Expected a mapping in {path.as_posix()}.",
        fix="Provide a mapping with entry or command and resource limits.",
        example='sandboxes:\n  summarize:\n    entry: "plugins.summarize:run"\n    timeout_seconds: 10',
    )


def _missing_entry_message(path: Path, flow_name: str) -> str:
    return build_guidance_message(
        what=f"Sandbox entry for '{flow_name}' is missing an entry or command.",
        why=f"Each sandbox entry needs an entry or command in {path.as_posix()}.",
        fix="Provide a module:function entry or a command.",
        example='sandboxes:\n  summarize:\n    entry: "plugins.summarize:run"',
    )


def _invalid_field_message(path: Path, flow_name: str, field: str) -> str:
    return build_guidance_message(
        what=f"Sandbox entry for '{flow_name}' has invalid {field}.",
        why=f"{field} must be text in {path.as_posix()}.",
        fix="Provide a text value.",
        example='image: "namel3ss/sandbox-base:latest"',
    )


def _invalid_limit_message(path: Path, flow_name: str, field: str) -> str:
    return build_guidance_message(
        what=f"Sandbox entry for '{flow_name}' has invalid {field}.",
        why=f"{field} must be a positive number in {path.as_posix()}.",
        fix=f"Provide a positive integer for {field}.",
        example=f"{field}: 10",
    )


__all__ = ["SandboxConfig", "SandboxFlow", "load_sandbox_config", "save_sandbox_config", "sandbox_path"]
