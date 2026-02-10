from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.ui.plugins import UIPluginRegistry, load_ui_plugin_registry

from .plugin_manifest import PluginManifestContract
from .plugin_registry import PluginRegistryContract, build_plugin_registry_contract


@dataclass(frozen=True)
class LoadedPlugin:
    manifest: PluginManifestContract


def load_plugins(
    plugin_names: tuple[str, ...],
    *,
    project_root: str | Path | None,
    app_path: str | Path | None,
    capabilities: tuple[str, ...],
    studio_mode: bool = False,
) -> tuple[LoadedPlugin, ...]:
    unique_names = tuple(sorted({str(name).strip() for name in plugin_names if str(name).strip()}))
    if not unique_names:
        return tuple()

    normalized_capabilities = {str(item).strip().lower() for item in capabilities}
    has_plugins_capability = "ui.plugins" in normalized_capabilities
    has_legacy_plugin_caps = {"custom_ui", "sandbox"}.issubset(normalized_capabilities)
    if not studio_mode and not has_plugins_capability and not has_legacy_plugin_caps:
        raise Namel3ssError(
            "Missing capabilities: ui.plugins. Add ui.plugins to enable plugin declarations outside Studio."
        )

    expanded_capabilities = set(normalized_capabilities)
    if has_plugins_capability:
        expanded_capabilities.update({"custom_ui", "sandbox"})

    # Build deterministic manifest contracts first (ordered by name/version).
    contract: PluginRegistryContract = build_plugin_registry_contract(
        unique_names,
        project_root=project_root,
        app_path=app_path,
    )
    contract_by_name = {item.name: item for item in contract.plugins}

    # Load executable plugin schemas through the existing sandboxed runtime loader.
    runtime_registry: UIPluginRegistry = load_ui_plugin_registry(
        plugin_names=unique_names,
        project_root=project_root,
        app_path=app_path,
        allowed_capabilities=tuple(sorted(expanded_capabilities)),
    )

    loaded: list[LoadedPlugin] = []
    for schema in sorted(runtime_registry.plugin_schemas, key=lambda item: (item.name, str(item.version or "0.1.0"))):
        manifest = contract_by_name.get(schema.name)
        if manifest is None:
            continue
        loaded.append(LoadedPlugin(manifest=manifest))
    return tuple(loaded)


__all__ = ["LoadedPlugin", "load_plugins"]
