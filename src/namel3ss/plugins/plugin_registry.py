from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.ui.plugins.loader import load_plugin_schema, resolve_plugin_directories

from .plugin_manifest import PluginManifestContract, parse_plugin_manifest_contract


@dataclass(frozen=True)
class PluginRegistryContract:
    plugins: tuple[PluginManifestContract, ...]

    @property
    def plugin_names(self) -> tuple[str, ...]:
        return tuple(item.name for item in self.plugins)


def build_plugin_registry_contract(
    plugin_names: tuple[str, ...],
    *,
    project_root: str | Path | None,
    app_path: str | Path | None,
) -> PluginRegistryContract:
    directories = resolve_plugin_directories(project_root=project_root, app_path=app_path)
    collected: list[PluginManifestContract] = []
    seen: set[str] = set()
    for name in sorted(plugin_names):
        if not name:
            continue
        schema = load_plugin_schema(name, directories=directories)
        contract = parse_plugin_manifest_contract(
            {
                "name": schema.name,
                "version": schema.version or "0.1.0",
                "module": schema.module_path.name,
                "capabilities": list(schema.capabilities),
                "permissions": list(schema.permissions),
                "components": [
                    {
                        "name": component.name,
                        "props": {
                            prop_name: {
                                "type": prop.type_name,
                                "required": prop.required,
                            }
                            for prop_name, prop in component.props.items()
                        },
                        "events": list(component.events),
                    }
                    for component in schema.components
                ],
            },
            source_path=(schema.plugin_root / "plugin.json").resolve(),
            plugin_root=schema.plugin_root,
        )
        if contract.name in seen:
            raise Namel3ssError(f"Duplicate plugin '{contract.name}' in registry contract.")
        seen.add(contract.name)
        collected.append(contract)
    ordered = tuple(sorted(collected, key=lambda item: (item.name, item.version)))
    return PluginRegistryContract(plugins=ordered)


__all__ = ["PluginRegistryContract", "build_plugin_registry_contract"]
