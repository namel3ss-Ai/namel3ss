from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from namel3ss.config.model import AppConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.packs.layout import pack_bindings_path, pack_manifest_path, packs_root
from namel3ss.runtime.packs.manifest import PackManifest, parse_pack_manifest
from namel3ss.runtime.packs.verification import load_pack_verification
from namel3ss.runtime.tools.bindings_yaml import ToolBinding, parse_bindings_yaml
from namel3ss.runtime.tools.runners.registry import list_runners
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
                version=get_tool_pack_binding(tools[0]).version if tools else "v1",
                description="Built-in tool pack",
                author="namel3ss",
                license="MIT",
                tools=sorted(tools),
                source="builtin_pack",
                verified=True,
                enabled=True,
                bindings=bindings,
                pack_root=None,
                errors=[],
            )
        )
    return records


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
    manifest_path = pack_manifest_path(pack_dir)
    if not manifest_path.exists():
        return None
    errors: list[str] = []
    manifest: PackManifest | None = None
    try:
        manifest = parse_pack_manifest(manifest_path)
    except Namel3ssError as err:
        errors.append(str(err))
    if manifest is None:
        return PackRecord(
            pack_id=pack_dir.name,
            name=pack_dir.name,
            version="",
            description="",
            author="",
            license="",
            tools=[],
            source="installed_pack",
            verified=False,
            enabled=False,
            bindings={},
            pack_root=pack_dir,
            errors=errors,
        )
    bindings, binding_errors = _load_pack_bindings(pack_dir, manifest)
    errors.extend(binding_errors)
    verified = _is_pack_verified(pack_dir, manifest, bindings)
    enabled = _is_pack_enabled(config, manifest.pack_id)
    return PackRecord(
        pack_id=manifest.pack_id,
        name=manifest.name,
        version=manifest.version,
        description=manifest.description,
        author=manifest.author,
        license=manifest.license,
        tools=manifest.tools,
        source="installed_pack",
        verified=verified,
        enabled=enabled,
        bindings=bindings,
        pack_root=pack_dir,
        errors=errors,
    )


def _load_pack_bindings(pack_dir: Path, manifest: PackManifest) -> tuple[dict[str, ToolBinding], list[str]]:
    errors: list[str] = []
    bindings: dict[str, ToolBinding] = {}
    bindings_path = pack_bindings_path(pack_dir)
    if bindings_path.exists():
        try:
            text = bindings_path.read_text(encoding="utf-8")
            bindings = parse_bindings_yaml(text, bindings_path)
        except Namel3ssError as err:
            errors.append(str(err))
    elif manifest.entrypoints:
        bindings = dict(manifest.entrypoints)
    else:
        errors.append(_missing_bindings_error(manifest.pack_id))
    _apply_manifest_defaults(bindings, manifest)
    _validate_pack_tools(manifest, bindings, errors)
    return bindings, errors


def _apply_manifest_defaults(bindings: dict[str, ToolBinding], manifest: PackManifest) -> None:
    for name, binding in list(bindings.items()):
        runner = binding.runner or manifest.runners_default
        url = binding.url
        image = binding.image
        command = binding.command
        env = binding.env
        sandbox = binding.sandbox
        enforcement = binding.enforcement
        if runner == "service" and not url:
            url = manifest.service_url
        if runner == "container" and not image:
            image = manifest.container_image
        if runner == "local" and sandbox is None:
            sandbox = True
        bindings[name] = ToolBinding(
            kind=binding.kind,
            entry=binding.entry,
            runner=runner,
            url=url,
            image=image,
            command=command,
            env=env,
            purity=binding.purity,
            timeout_ms=binding.timeout_ms,
            sandbox=sandbox,
            enforcement=enforcement,
        )


def _validate_pack_tools(manifest: PackManifest, bindings: dict[str, ToolBinding], errors: list[str]) -> None:
    if not manifest.tools:
        errors.append(_missing_tools_error(manifest.pack_id))
        return
    for tool_name in manifest.tools:
        if tool_name not in bindings:
            errors.append(_missing_tool_binding_error(manifest.pack_id, tool_name))
    for tool_name, binding in bindings.items():
        if tool_name not in manifest.tools:
            errors.append(_unexpected_tool_binding_error(manifest.pack_id, tool_name))
        if binding.kind != "python":
            errors.append(_invalid_binding_kind_error(manifest.pack_id, tool_name))
        if binding.runner and binding.runner not in list_runners():
            errors.append(_invalid_binding_runner_error(manifest.pack_id, tool_name))
        if binding.runner == "service" and not (binding.url or manifest.service_url):
            errors.append(_missing_service_url_error(manifest.pack_id, tool_name))
        if binding.runner == "container" and not (binding.image or manifest.container_image):
            errors.append(_missing_container_image_error(manifest.pack_id, tool_name))


def _is_pack_verified(pack_dir: Path, manifest: PackManifest, bindings: dict[str, ToolBinding]) -> bool:
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
    verification = load_pack_verification(pack_dir, manifest_text, tools_text)
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


def _missing_bindings_error(pack_id: str) -> str:
    return build_guidance_message(
        what=f'Pack "{pack_id}" is missing tool bindings.',
        why="Provide tools.yaml or entrypoints in pack.yaml.",
        fix="Add tools.yaml or entrypoints to the pack.",
        example="tools.yaml",
    )


def _missing_tools_error(pack_id: str) -> str:
    return build_guidance_message(
        what=f'Pack "{pack_id}" is missing tools.',
        why="pack.yaml must list tools provided by the pack.",
        fix="Add tools to pack.yaml.",
        example='tools:\\n  - "greet someone"',
    )


def _missing_tool_binding_error(pack_id: str, tool_name: str) -> str:
    return build_guidance_message(
        what=f'Pack "{pack_id}" is missing binding for "{tool_name}".',
        why="Every tool listed in pack.yaml must have a binding.",
        fix="Add the tool to tools.yaml or entrypoints.",
        example=f'"{tool_name}":\\n  kind: "python"\\n  entry: "tools.my_tool:run"',
    )


def _unexpected_tool_binding_error(pack_id: str, tool_name: str) -> str:
    return build_guidance_message(
        what=f'Pack "{pack_id}" binding "{tool_name}" is unexpected.',
        why="tools.yaml includes a tool not listed in pack.yaml.",
        fix="Add the tool to pack.yaml or remove it from tools.yaml.",
        example='tools:\\n  - "greet someone"',
    )


def _invalid_binding_kind_error(pack_id: str, tool_name: str) -> str:
    return build_guidance_message(
        what=f'Pack "{pack_id}" tool "{tool_name}" has invalid kind.',
        why="Only python tool kinds are supported.",
        fix="Set kind to python.",
        example='kind: "python"',
    )


def _invalid_binding_runner_error(pack_id: str, tool_name: str) -> str:
    return build_guidance_message(
        what=f'Pack "{pack_id}" tool "{tool_name}" has invalid runner.',
        why="Runner must be local, service, or container.",
        fix="Update runner or remove it.",
        example='runner: "local"',
    )


def _missing_service_url_error(pack_id: str, tool_name: str) -> str:
    return build_guidance_message(
        what=f'Pack "{pack_id}" tool "{tool_name}" requires a service URL.',
        why="Runner is service but no URL was configured.",
        fix="Set service_url in pack.yaml or url in tools.yaml.",
        example='service_url: "http://127.0.0.1:8787/tools"',
    )


def _missing_container_image_error(pack_id: str, tool_name: str) -> str:
    return build_guidance_message(
        what=f'Pack "{pack_id}" tool "{tool_name}" requires a container image.',
        why="Runner is container but no image was configured.",
        fix="Set container.image in pack.yaml or image in tools.yaml.",
        example='image: "ghcr.io/namel3ss/tools:latest"',
    )

def pack_payload(pack: PackRecord) -> dict[str, object]:
    return {
        "pack_id": pack.pack_id,
        "name": pack.name,
        "version": pack.version,
        "description": pack.description,
        "author": pack.author,
        "license": pack.license,
        "tools": list(pack.tools),
        "source": pack.source,
        "verified": pack.verified,
        "enabled": pack.enabled,
        "errors": list(pack.errors),
    }


__all__ = ["PackRecord", "PackRegistry", "PackTool", "load_pack_registry", "pack_payload"]
