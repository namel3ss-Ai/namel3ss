from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from namel3ss.config.model import AppConfig
from namel3ss.runtime.packs.layout import pack_bindings_path, pack_manifest_path, packs_root
from namel3ss.runtime.packs.manifest import PackManifest
from namel3ss.runtime.packs.pack_loader import load_local_pack_items
from namel3ss.runtime.packs.pack_manifest import PackContents, load_pack_contents
from namel3ss.runtime.packs.verification import load_pack_verification
from namel3ss.runtime.tools.bindings_yaml import ToolBinding
from namel3ss.runtime.tools.tool_pack_registry import get_tool_pack_binding, list_tool_pack_tools


@dataclass(frozen=True)
class PackTool:
    tool_name: str
    pack_id: str
    pack_name: str
    pack_version: str
    source: str
    verified: bool
    enabled: bool
    binding: ToolBinding
    pack_root: Path | None


@dataclass(frozen=True)
class PackRecord:
    pack_id: str
    name: str
    version: str
    description: str
    author: str
    license: str
    tools: list[str]
    signer_id: str | None
    source: str
    verified: bool
    enabled: bool
    bindings: dict[str, ToolBinding]
    pack_root: Path | None
    errors: list[str]


@dataclass(frozen=True)
class PackRegistry:
    packs: dict[str, PackRecord]
    tools: dict[str, list[PackTool]]
    collisions: dict[str, list[PackTool]]


def load_pack_registry(app_root: Path, config: AppConfig) -> PackRegistry:
    packs: dict[str, PackRecord] = {}
    tools: dict[str, list[PackTool]] = {}
    for pack in _load_builtin_packs():
        packs[pack.pack_id] = pack
        for name, binding in pack.bindings.items():
            tools.setdefault(name, []).append(
                PackTool(
                    tool_name=name,
                    pack_id=pack.pack_id,
                    pack_name=pack.name,
                    pack_version=pack.version,
                    source=pack.source,
                    verified=pack.verified,
                    enabled=pack.enabled,
                    binding=binding,
                    pack_root=pack.pack_root,
                )
            )
    for pack in _load_local_packs(app_root):
        packs[pack.pack_id] = pack
        for name, binding in pack.bindings.items():
            tools.setdefault(name, []).append(
                PackTool(
                    tool_name=name,
                    pack_id=pack.pack_id,
                    pack_name=pack.name,
                    pack_version=pack.version,
                    source=pack.source,
                    verified=pack.verified,
                    enabled=pack.enabled,
                    binding=binding,
                    pack_root=pack.pack_root,
                )
            )
    for pack in _load_installed_packs(app_root, config):
        packs[pack.pack_id] = pack
        for name, binding in pack.bindings.items():
            tools.setdefault(name, []).append(
                PackTool(
                    tool_name=name,
                    pack_id=pack.pack_id,
                    pack_name=pack.name,
                    pack_version=pack.version,
                    source=pack.source,
                    verified=pack.verified,
                    enabled=pack.enabled,
                    binding=binding,
                    pack_root=pack.pack_root,
                )
            )
    collisions = {name: items for name, items in tools.items() if len(items) > 1}
    return PackRegistry(packs=packs, tools=tools, collisions=collisions)


def _load_builtin_packs() -> list[PackRecord]:
    grouped: dict[str, list[str]] = {}
    for tool_name in list_tool_pack_tools():
        binding = get_tool_pack_binding(tool_name)
        if not binding:
            continue
        grouped.setdefault(binding.pack_name, []).append(tool_name)
    records: list[PackRecord] = []
    for pack_name, tools in grouped.items():
        pack_id = f"builtin.{pack_name}"
        bindings: dict[str, ToolBinding] = {}
        for tool_name in tools:
            binding = get_tool_pack_binding(tool_name)
            if binding:
                bindings[tool_name] = ToolBinding(kind="python", entry=binding.entry, sandbox=True)
        records.append(
            PackRecord(
                pack_id=pack_id,
                name=pack_name,
                version=get_tool_pack_binding(tools[0]).version if tools else "stable",
                description="Built-in tool pack",
                author="namel3ss",
                license="MIT",
                tools=sorted(tools),
                signer_id="namel3ss",
                source="builtin_pack",
                verified=True,
                enabled=True,
                bindings=bindings,
                pack_root=None,
                errors=[],
            )
        )
    return records


def _load_local_packs(app_root: Path) -> list[PackRecord]:
    records: list[PackRecord] = []
    for item in load_local_pack_items(app_root):
        record = _local_pack_record(item.pack_dir, item.contents, app_root=app_root)
        if record:
            records.append(record)
    return records


def _local_pack_record(pack_dir: Path, contents: PackContents, *, app_root: Path) -> PackRecord | None:
    manifest = contents.manifest
    errors = list(contents.errors)
    if manifest is None:
        return PackRecord(
            pack_id=pack_dir.name,
            name=pack_dir.name,
            version="",
            description="",
            author="",
            license="",
            tools=[],
            signer_id=None,
            source="local_pack",
            verified=False,
            enabled=True,
            bindings={},
            pack_root=pack_dir,
            errors=errors,
        )
    verified = _is_pack_verified(pack_dir, manifest, contents.bindings, app_root=app_root)
    return PackRecord(
        pack_id=manifest.pack_id,
        name=manifest.name,
        version=manifest.version,
        description=manifest.description,
        author=manifest.author,
        license=manifest.license,
        tools=manifest.tools,
        signer_id=manifest.signer_id,
        source="local_pack",
        verified=verified,
        enabled=True,
        bindings=contents.bindings,
        pack_root=pack_dir,
        errors=errors,
    )


def _load_installed_packs(app_root: Path, config: AppConfig) -> list[PackRecord]:
    root = packs_root(app_root)
    if not root.exists():
        return []
    records: list[PackRecord] = []
    for pack_dir in sorted(path for path in root.iterdir() if path.is_dir()):
        record = _load_installed_pack(pack_dir, app_root, config)
        if record:
            records.append(record)
    return records


def _load_installed_pack(pack_dir: Path, app_root: Path, config: AppConfig) -> PackRecord | None:
    contents = load_pack_contents(pack_dir)
    manifest = contents.manifest
    if manifest is None:
        return PackRecord(
            pack_id=pack_dir.name,
            name=pack_dir.name,
            version="",
            description="",
            author="",
            license="",
            tools=[],
            signer_id=None,
            source="installed_pack",
            verified=False,
            enabled=False,
            bindings={},
            pack_root=pack_dir,
            errors=list(contents.errors),
        )
    errors = list(contents.errors)
    verified = _is_pack_verified(pack_dir, manifest, contents.bindings, app_root=app_root)
    enabled = _is_pack_enabled(config, manifest.pack_id)
    return PackRecord(
        pack_id=manifest.pack_id,
        name=manifest.name,
        version=manifest.version,
        description=manifest.description,
        author=manifest.author,
        license=manifest.license,
        tools=manifest.tools,
        signer_id=manifest.signer_id,
        source="installed_pack",
        verified=verified,
        enabled=enabled,
        bindings=contents.bindings,
        pack_root=pack_dir,
        errors=errors,
    )


def _is_pack_verified(
    pack_dir: Path,
    manifest: PackManifest,
    bindings: dict[str, ToolBinding],
    *,
    app_root: Path,
) -> bool:
    try:
        manifest_text = pack_manifest_path(pack_dir).read_text(encoding="utf-8")
    except Exception:
        return False
    tools_text = None
    bindings_path = pack_bindings_path(pack_dir)
    if bindings_path.exists():
        try:
            tools_text = bindings_path.read_text(encoding="utf-8")
        except Exception:
            tools_text = None
    verification = load_pack_verification(pack_dir, manifest_text, tools_text, app_root=app_root)
    if not verification.verified:
        return False
    if verification.pack_id and verification.pack_id != manifest.pack_id:
        return False
    if verification.version and verification.version != manifest.version:
        return False
    return True


def _is_pack_enabled(config: AppConfig, pack_id: str) -> bool:
    enabled = set(config.tool_packs.enabled_packs)
    disabled = set(config.tool_packs.disabled_packs)
    if pack_id in disabled:
        return False
    if enabled:
        return pack_id in enabled
    return False


def pack_payload(pack: PackRecord) -> dict[str, object]:
    return {
        "pack_id": pack.pack_id,
        "name": pack.name,
        "version": pack.version,
        "description": pack.description,
        "author": pack.author,
        "license": pack.license,
        "tools": list(pack.tools),
        "signer_id": pack.signer_id,
        "source": pack.source,
        "verified": pack.verified,
        "enabled": pack.enabled,
        "errors": list(pack.errors),
    }


__all__ = ["PackRecord", "PackRegistry", "PackTool", "load_pack_registry", "pack_payload"]
