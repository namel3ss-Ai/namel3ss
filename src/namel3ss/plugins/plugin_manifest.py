from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from namel3ss.errors.base import Namel3ssError
from namel3ss.ui.plugins.schema import UIPluginSchema, parse_plugin_manifest
from namel3ss.utils.simple_yaml import parse_yaml


@dataclass(frozen=True)
class PluginComponentContract:
    name: str
    props: tuple[str, ...]
    events: tuple[str, ...]


@dataclass(frozen=True)
class PluginManifestContract:
    name: str
    version: str
    capabilities: tuple[str, ...]
    permissions: tuple[str, ...]
    components: tuple[PluginComponentContract, ...]
    entry_point: str


def parse_plugin_manifest_contract(payload: Mapping[str, object], *, source_path: Path, plugin_root: Path) -> PluginManifestContract:
    schema = parse_plugin_manifest(payload, source_path=source_path, plugin_root=plugin_root)
    return _from_ui_plugin_schema(schema)


def load_plugin_manifest_contract(manifest_path: Path, *, plugin_root: Path | None = None) -> PluginManifestContract:
    payload = _read_manifest_file(manifest_path)
    root = (plugin_root or manifest_path.parent).resolve()
    return parse_plugin_manifest_contract(payload, source_path=manifest_path.resolve(), plugin_root=root)


def _from_ui_plugin_schema(schema: UIPluginSchema) -> PluginManifestContract:
    components: list[PluginComponentContract] = []
    for component in schema.components:
        props = tuple(sorted(component.props.keys()))
        events = tuple(sorted(component.events))
        components.append(
            PluginComponentContract(
                name=component.name,
                props=props,
                events=events,
            )
        )
    return PluginManifestContract(
        name=schema.name,
        version=str(schema.version or "0.1.0"),
        capabilities=tuple(sorted(schema.capabilities)),
        permissions=tuple(sorted(schema.permissions)),
        components=tuple(sorted(components, key=lambda item: item.name)),
        entry_point=schema.module_path.name,
    )


def _read_manifest_file(path: Path) -> Mapping[str, object]:
    raw = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    if suffix == ".json":
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as err:
            raise Namel3ssError(
                f"Invalid plugin manifest JSON at {path.as_posix()}: {err.msg}",
                line=err.lineno,
                column=err.colno,
            ) from err
    else:
        payload = parse_yaml(raw)
    if not isinstance(payload, Mapping):
        raise Namel3ssError(f"Plugin manifest at {path.as_posix()} must be a mapping.")
    return payload


__all__ = [
    "PluginComponentContract",
    "PluginManifestContract",
    "load_plugin_manifest_contract",
    "parse_plugin_manifest_contract",
]
