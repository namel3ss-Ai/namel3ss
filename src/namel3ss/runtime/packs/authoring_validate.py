from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.packs.capabilities import load_pack_capabilities
from namel3ss.runtime.packs.intent import load_intent, validate_intent
from namel3ss.runtime.packs.layout import pack_bindings_path, pack_manifest_path
from namel3ss.runtime.packs.manifest import PackManifest, parse_pack_manifest
from namel3ss.runtime.tools.bindings_yaml import ToolBinding, parse_bindings_yaml
from namel3ss.runtime.tools.runners.registry import list_runners


@dataclass(frozen=True)
class PackIssue:
    severity: str
    message: str


@dataclass(frozen=True)
class PackValidationResult:
    pack_id: str
    issues: list[PackIssue]

    @property
    def errors(self) -> list[PackIssue]:
        return [issue for issue in self.issues if issue.severity == "error"]

    @property
    def warnings(self) -> list[PackIssue]:
        return [issue for issue in self.issues if issue.severity == "warning"]


def validate_pack(pack_dir: Path) -> PackValidationResult:
    issues: list[PackIssue] = []
    manifest = _load_manifest(pack_dir, issues)
    if manifest is None:
        return PackValidationResult(pack_id=pack_dir.name, issues=issues)
    bindings = _load_bindings(pack_dir, manifest, issues)
    _validate_intent(pack_dir, issues)
    capabilities = _load_capabilities(pack_dir, issues)
    _validate_capabilities(manifest, bindings, capabilities, issues)
    return PackValidationResult(pack_id=manifest.pack_id, issues=issues)


def _load_manifest(pack_dir: Path, issues: list[PackIssue]) -> PackManifest | None:
    manifest_path = pack_manifest_path(pack_dir)
    if not manifest_path.exists():
        issues.append(PackIssue("error", _missing_manifest_message(manifest_path)))
        return None
    try:
        return parse_pack_manifest(manifest_path)
    except Namel3ssError as err:
        issues.append(PackIssue("error", str(err)))
        return None


def _load_bindings(
    pack_dir: Path,
    manifest: PackManifest,
    issues: list[PackIssue],
) -> dict[str, ToolBinding]:
    bindings: dict[str, ToolBinding] = {}
    bindings_path = pack_bindings_path(pack_dir)
    has_entrypoints = bool(manifest.entrypoints)
    if bindings_path.exists():
        try:
            bindings_text = bindings_path.read_text(encoding="utf-8")
            bindings = parse_bindings_yaml(bindings_text, bindings_path)
        except Namel3ssError as err:
            issues.append(PackIssue("error", str(err)))
            return {}
        if has_entrypoints:
            issues.append(PackIssue("warning", _both_bindings_message(manifest.pack_id)))
    elif has_entrypoints:
        bindings = dict(manifest.entrypoints or {})
    else:
        issues.append(PackIssue("error", _missing_bindings_message(manifest.pack_id)))
        return {}
    _apply_manifest_defaults(bindings, manifest)
    _validate_bindings(manifest, bindings, issues)
    return bindings


def _validate_intent(pack_dir: Path, issues: list[PackIssue]) -> None:
    try:
        text = load_intent(pack_dir)
    except Namel3ssError as err:
        issues.append(PackIssue("error", str(err)))
        return
    for message in validate_intent(text, pack_dir / "intent.md"):
        issues.append(PackIssue("error", message))


def _load_capabilities(pack_dir: Path, issues: list[PackIssue]) -> dict:
    try:
        return load_pack_capabilities(pack_dir)
    except Namel3ssError as err:
        issues.append(PackIssue("error", str(err)))
        return {}


def _validate_capabilities(
    manifest: PackManifest,
    bindings: dict[str, ToolBinding],
    capabilities: dict[str, object],
    issues: list[PackIssue],
) -> None:
    for tool in manifest.tools:
        binding = bindings.get(tool)
        if binding is None:
            continue
        runner = binding.runner or manifest.runners_default or "local"
        purity = binding.purity or "impure"
        requires_caps = not (runner == "local" and purity == "pure")
        tool_caps = capabilities.get(tool)
        if requires_caps and tool_caps is None:
            issues.append(PackIssue("warning", _missing_capabilities_message(manifest.pack_id, tool)))
            continue
        if tool_caps is None:
            continue
        if runner == "service" and getattr(tool_caps, "network", None) != "outbound":
            issues.append(PackIssue("warning", _service_caps_message(manifest.pack_id, tool)))
        if runner == "container" and getattr(tool_caps, "subprocess", None) != "allow":
            issues.append(PackIssue("warning", _container_caps_message(manifest.pack_id, tool)))
    extra = sorted(name for name in capabilities.keys() if name not in manifest.tools)
    for name in extra:
        issues.append(PackIssue("warning", _unknown_tool_caps_message(manifest.pack_id, name)))


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


def _validate_bindings(manifest: PackManifest, bindings: dict[str, ToolBinding], issues: list[PackIssue]) -> None:
    if not manifest.tools:
        issues.append(PackIssue("error", _missing_tools_message(manifest.pack_id)))
        return
    valid_runners = set(list_runners())
    for tool_name in manifest.tools:
        if tool_name not in bindings:
            issues.append(PackIssue("error", _missing_tool_binding_message(manifest.pack_id, tool_name)))
    for tool_name, binding in bindings.items():
        if tool_name not in manifest.tools:
            issues.append(PackIssue("error", _unexpected_tool_binding_message(manifest.pack_id, tool_name)))
        if binding.kind != "python":
            issues.append(PackIssue("error", _invalid_binding_kind_message(manifest.pack_id, tool_name)))
        if binding.runner and binding.runner not in valid_runners:
            issues.append(PackIssue("error", _invalid_binding_runner_message(manifest.pack_id, tool_name)))
        if binding.runner == "service" and not (binding.url or manifest.service_url):
            issues.append(PackIssue("error", _missing_service_url_message(manifest.pack_id, tool_name)))
        if binding.runner == "container" and not (binding.image or manifest.container_image):
            issues.append(PackIssue("error", _missing_container_image_message(manifest.pack_id, tool_name)))


def _missing_manifest_message(path: Path) -> str:
    return build_guidance_message(
        what="Pack manifest is missing.",
        why=f"Expected pack.yaml in {path.as_posix()}.",
        fix="Add pack.yaml or re-run `n3 packs init`.",
        example="pack.yaml",
    )


def _missing_bindings_message(pack_id: str) -> str:
    return build_guidance_message(
        what=f'Pack "{pack_id}" is missing tool bindings.',
        why="Provide tools.yaml or entrypoints in pack.yaml.",
        fix="Add tools.yaml or entrypoints to the pack.",
        example="tools.yaml",
    )


def _both_bindings_message(pack_id: str) -> str:
    return build_guidance_message(
        what=f'Pack "{pack_id}" includes both tools.yaml and entrypoints.',
        why="Tools can be defined in either file, but using both can be confusing.",
        fix="Remove one source of bindings.",
        example="Remove entrypoints or tools.yaml.",
    )


def _missing_tools_message(pack_id: str) -> str:
    return build_guidance_message(
        what=f'Pack "{pack_id}" is missing tools.',
        why="pack.yaml must list tools provided by the pack.",
        fix="Add tools to pack.yaml.",
        example='tools:\n  - "greet someone"',
    )


def _missing_tool_binding_message(pack_id: str, tool_name: str) -> str:
    return build_guidance_message(
        what=f'Pack "{pack_id}" is missing binding for "{tool_name}".',
        why="Every tool listed in pack.yaml must have a binding.",
        fix="Add the tool to tools.yaml or entrypoints.",
        example=f'"{tool_name}":\n  kind: "python"\n  entry: "tools.my_tool:run"',
    )


def _unexpected_tool_binding_message(pack_id: str, tool_name: str) -> str:
    return build_guidance_message(
        what=f'Pack "{pack_id}" binding "{tool_name}" is unexpected.',
        why="tools.yaml includes a tool not listed in pack.yaml.",
        fix="Add the tool to pack.yaml or remove it from tools.yaml.",
        example='tools:\n  - "greet someone"',
    )


def _invalid_binding_kind_message(pack_id: str, tool_name: str) -> str:
    return build_guidance_message(
        what=f'Pack "{pack_id}" tool "{tool_name}" has invalid kind.',
        why="Only python tool kinds are supported.",
        fix="Set kind to python.",
        example='kind: "python"',
    )


def _invalid_binding_runner_message(pack_id: str, tool_name: str) -> str:
    return build_guidance_message(
        what=f'Pack "{pack_id}" tool "{tool_name}" has invalid runner.',
        why="Runner must be local, service, or container.",
        fix="Update runner or remove it.",
        example='runner: "local"',
    )


def _missing_service_url_message(pack_id: str, tool_name: str) -> str:
    return build_guidance_message(
        what=f'Pack "{pack_id}" tool "{tool_name}" requires a service URL.',
        why="Runner is service but no URL was configured.",
        fix="Set service_url in pack.yaml or url in tools.yaml.",
        example='service_url: "http://127.0.0.1:8787/tools"',
    )


def _missing_container_image_message(pack_id: str, tool_name: str) -> str:
    return build_guidance_message(
        what=f'Pack "{pack_id}" tool "{tool_name}" requires a container image.',
        why="Runner is container but no image was configured.",
        fix="Set container.image in pack.yaml or image in tools.yaml.",
        example='image: "ghcr.io/namel3ss/tools:latest"',
    )


def _missing_capabilities_message(pack_id: str, tool_name: str) -> str:
    return build_guidance_message(
        what=f'Pack "{pack_id}" tool "{tool_name}" is missing capabilities.',
        why="Non-pure tools must declare capabilities in capabilities.yaml.",
        fix="Add capability entries for the tool.",
        example='capabilities:\n  "tool name":\n    filesystem: "read"\n    network: "outbound"\n    env: "none"\n    subprocess: "none"\n    secrets: []',
    )


def _service_caps_message(pack_id: str, tool_name: str) -> str:
    return build_guidance_message(
        what=f'Pack "{pack_id}" tool "{tool_name}" must declare network outbound.',
        why="Service runners call external URLs.",
        fix='Set network: "outbound" for the tool.',
        example='network: "outbound"',
    )


def _container_caps_message(pack_id: str, tool_name: str) -> str:
    return build_guidance_message(
        what=f'Pack "{pack_id}" tool "{tool_name}" must declare subprocess allow.',
        why="Container runners spawn local container processes.",
        fix='Set subprocess: "allow" for the tool.',
        example='subprocess: "allow"',
    )


def _unknown_tool_caps_message(pack_id: str, tool_name: str) -> str:
    return build_guidance_message(
        what=f'Pack "{pack_id}" has capabilities for unknown tool "{tool_name}".',
        why="capabilities.yaml includes a tool not listed in pack.yaml.",
        fix="Add the tool to pack.yaml or remove it from capabilities.yaml.",
        example='tools:\n  - "tool name"',
    )


__all__ = ["PackIssue", "PackValidationResult", "validate_pack"]
