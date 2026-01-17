from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.packs.capabilities import ToolCapabilities, load_pack_capabilities
from namel3ss.runtime.packs.layout import pack_bindings_path, pack_manifest_path
from namel3ss.runtime.packs.manifest import PackManifest, parse_pack_manifest
from namel3ss.runtime.tools.bindings_yaml import ToolBinding, parse_bindings_yaml
from namel3ss.runtime.tools.runners.registry import list_runners


@dataclass(frozen=True)
class PackContents:
    manifest: PackManifest | None
    bindings: dict[str, ToolBinding]
    capabilities: dict[str, ToolCapabilities]
    errors: list[str]


def load_pack_contents(pack_dir: Path) -> PackContents:
    errors: list[str] = []
    manifest_path = pack_manifest_path(pack_dir)
    if not manifest_path.exists():
        return PackContents(
            manifest=None,
            bindings={},
            capabilities={},
            errors=[_missing_manifest_error(pack_dir)],
        )
    manifest: PackManifest | None = None
    try:
        manifest = parse_pack_manifest(manifest_path)
    except Namel3ssError as err:
        errors.append(str(err))
    bindings: dict[str, ToolBinding] = {}
    if manifest:
        bindings, binding_errors = load_pack_bindings(pack_dir, manifest)
        errors.extend(binding_errors)
    capabilities: dict[str, ToolCapabilities] = {}
    try:
        capabilities = load_pack_capabilities(pack_dir)
    except Namel3ssError as err:
        errors.append(str(err))
        capabilities = {}
    return PackContents(
        manifest=manifest,
        bindings=bindings,
        capabilities=capabilities,
        errors=errors,
    )


def load_pack_bindings(pack_dir: Path, manifest: PackManifest) -> tuple[dict[str, ToolBinding], list[str]]:
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


def _missing_manifest_error(pack_dir: Path) -> str:
    return build_guidance_message(
        what="Pack manifest is missing.",
        why=f"Expected pack.yaml under {pack_dir.as_posix()}.",
        fix="Add pack.yaml to the pack.",
        example="pack.yaml",
    )


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


__all__ = ["PackContents", "load_pack_bindings", "load_pack_contents"]
