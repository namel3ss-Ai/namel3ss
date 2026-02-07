from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from namel3ss.errors.base import Namel3ssError

from .hook_sandbox import load_sandboxed_hook
from .registry import UIPluginRegistry


@dataclass(frozen=True)
class LoadedHook:
    hook_type: str
    plugin_name: str
    plugin_version: str
    module_path: Path
    execute: object


@dataclass(frozen=True)
class RuntimeHookOutcome:
    blocked_message: str | None
    annotations: tuple[dict[str, object], ...]


class ExtensionHookManager:
    def __init__(self, hooks: tuple[LoadedHook, ...]) -> None:
        self._hooks = tuple(hooks)

    @property
    def has_hooks(self) -> bool:
        return bool(self._hooks)

    @property
    def hooks(self) -> tuple[LoadedHook, ...]:
        return self._hooks

    def run_compile_hooks(self, *, program) -> tuple[str, ...]:
        warnings: list[str] = []
        for hook in self._hooks:
            if hook.hook_type != "compiler":
                continue
            payload = _execute_hook(
                hook,
                {
                    "program": {
                        "spec_version": str(getattr(program, "spec_version", "") or ""),
                        "pages": [str(getattr(page, "name", "") or "") for page in list(getattr(program, "pages", []) or [])],
                        "flows": [str(getattr(flow, "name", "") or "") for flow in list(getattr(program, "flows", []) or [])],
                        "records": [str(getattr(record, "name", "") or "") for record in list(getattr(program, "records", []) or [])],
                    }
                },
            )
            warnings.extend(_collect_compile_warnings(hook, payload))
        return tuple(warnings)

    def run_runtime_tool_hooks(
        self,
        *,
        stage: str,
        tool_name: str,
        args: dict[str, object],
        result: object = None,
        error: str | None = None,
    ) -> RuntimeHookOutcome:
        blocked_message: str | None = None
        annotations: list[dict[str, object]] = []
        for hook in self._hooks:
            if hook.hook_type != "runtime":
                continue
            payload = _execute_hook(
                hook,
                {
                    "stage": str(stage),
                    "tool_name": str(tool_name),
                    "args": dict(args or {}),
                    "result": result,
                    "error": str(error) if error else "",
                },
            )
            hook_block_message, hook_annotations = _collect_runtime_payload(hook, payload)
            if blocked_message is None and hook_block_message:
                blocked_message = hook_block_message
            annotations.extend(hook_annotations)
        return RuntimeHookOutcome(blocked_message=blocked_message, annotations=tuple(annotations))

    def run_studio_hooks(self, *, session_id: str | None) -> tuple[dict[str, object], ...]:
        panels: list[dict[str, object]] = []
        for hook in self._hooks:
            if hook.hook_type != "studio":
                continue
            payload = _execute_hook(
                hook,
                {
                    "session_id": str(session_id or ""),
                },
            )
            panels.extend(_collect_studio_panels(hook, payload))
        return tuple(panels)


def build_extension_hook_manager(
    *,
    plugin_registry: UIPluginRegistry | None,
    capabilities: tuple[str, ...],
) -> ExtensionHookManager:
    if plugin_registry is None:
        return ExtensionHookManager(())
    capability_set = {str(item).strip().lower() for item in capabilities}
    if "hook_execution" not in capability_set and "extension_hooks" not in capability_set:
        return ExtensionHookManager(())
    hooks: list[LoadedHook] = []
    for schema in sorted(plugin_registry.plugin_schemas, key=lambda item: (item.name, str(item.version or "0.0.0"))):
        version = str(schema.version or "0.0.0")
        for hook_type, hook_path in sorted(schema.hooks, key=lambda entry: entry[0]):
            module_path = (schema.plugin_root / hook_path).resolve()
            execute = load_sandboxed_hook(module_path, hook_type=hook_type)
            hooks.append(
                LoadedHook(
                    hook_type=hook_type,
                    plugin_name=schema.name,
                    plugin_version=version,
                    module_path=module_path,
                    execute=execute,
                )
            )
    return ExtensionHookManager(tuple(hooks))


def _execute_hook(hook: LoadedHook, context: dict[str, object]) -> object:
    try:
        return hook.execute(context)  # type: ignore[misc]
    except Namel3ssError:
        raise
    except Exception as err:  # pragma: no cover - defensive
        raise Namel3ssError(
            (
                f"Extension hook '{hook.plugin_name}:{hook.hook_type}' failed "
                f"at {hook.module_path.as_posix()}: {err}"
            )
        ) from err


def _collect_compile_warnings(hook: LoadedHook, payload: object) -> list[str]:
    if isinstance(payload, str) and payload:
        return [f"{hook.plugin_name}@{hook.plugin_version}: {payload}"]
    if isinstance(payload, list):
        warnings: list[str] = []
        for item in payload:
            if isinstance(item, str) and item:
                warnings.append(f"{hook.plugin_name}@{hook.plugin_version}: {item}")
        return warnings
    if isinstance(payload, dict):
        value = payload.get("warnings")
        if isinstance(value, list):
            warnings = []
            for item in value:
                if isinstance(item, str) and item:
                    warnings.append(f"{hook.plugin_name}@{hook.plugin_version}: {item}")
            return warnings
    return []


def _collect_runtime_payload(
    hook: LoadedHook,
    payload: object,
) -> tuple[str | None, list[dict[str, object]]]:
    if not isinstance(payload, dict):
        return None, []
    blocked_message: str | None = None
    if bool(payload.get("block")):
        message = payload.get("message")
        if isinstance(message, str) and message.strip():
            blocked_message = f"{hook.plugin_name}: {message.strip()}"
        else:
            blocked_message = f"{hook.plugin_name}: tool call was blocked by runtime hook."
    annotation = {
        "plugin": hook.plugin_name,
        "version": hook.plugin_version,
        "hook_type": hook.hook_type,
        "payload": dict(payload),
    }
    return blocked_message, [annotation]


def _collect_studio_panels(hook: LoadedHook, payload: object) -> list[dict[str, object]]:
    if isinstance(payload, dict):
        return [_normalize_studio_panel(hook, payload)]
    if isinstance(payload, list):
        panels: list[dict[str, object]] = []
        for entry in payload:
            if isinstance(entry, dict):
                panels.append(_normalize_studio_panel(hook, entry))
        return panels
    return []


def _normalize_studio_panel(hook: LoadedHook, payload: dict[str, object]) -> dict[str, object]:
    panel = dict(payload)
    panel.setdefault("plugin", hook.plugin_name)
    panel.setdefault("version", hook.plugin_version)
    panel.setdefault("hook_type", hook.hook_type)
    return panel


__all__ = [
    "ExtensionHookManager",
    "LoadedHook",
    "RuntimeHookOutcome",
    "build_extension_hook_manager",
]
