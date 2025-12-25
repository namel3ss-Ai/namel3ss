from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from namel3ss.config.model import AppConfig, ToolPacksConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.capabilities.effective import build_effective_guarantees, summarize_guarantees
from namel3ss.runtime.packs.authoring_validate import PackIssue, PackValidationResult, validate_pack
from namel3ss.runtime.packs.capabilities import capabilities_by_tool, capabilities_summary, load_pack_capabilities
from namel3ss.runtime.packs.config import read_pack_config
from namel3ss.runtime.packs.intent import summarize_intent, load_intent
from namel3ss.runtime.packs.layout import pack_bindings_path
from namel3ss.runtime.packs.manifest import PackManifest, parse_pack_manifest
from namel3ss.runtime.packs.registry import load_pack_registry
from namel3ss.runtime.tools.bindings_yaml import ToolBinding, parse_bindings_yaml
from namel3ss.runtime.tools.tool_pack_registry import list_tool_pack_tools


@dataclass(frozen=True)
class PackReviewResult:
    status: str
    payload: dict[str, object]
    issues: list[PackIssue]


def review_pack(pack_dir: Path, app_root: Path | None) -> PackReviewResult:
    manifest = _load_manifest(pack_dir)
    validation = validate_pack(pack_dir)
    bindings = _load_bindings(pack_dir, manifest)
    runners = sorted({binding.runner or manifest.runners_default or "local" for binding in bindings.values()})
    tools = sorted(manifest.tools)
    intent_summary = _load_intent_summary(pack_dir, validation)
    caps = _safe_capabilities(pack_dir, validation)
    collisions = _find_collisions(tools, manifest.pack_id, app_root)
    collision_issues = [_collision_issue(manifest.pack_id, name) for name in collisions]
    issues = validation.issues + collision_issues
    status = _status_from_issues(issues)
    payload = {
        "pack_id": manifest.pack_id,
        "name": manifest.name,
        "version": manifest.version,
        "tools": tools,
        "runners": runners,
        "capabilities": {
            "summary": capabilities_summary(caps) if caps else {},
            "by_tool": capabilities_by_tool(caps) if caps else {},
        },
        "guarantees": {
            "summary": summarize_guarantees(caps) if caps else {},
            "by_tool": _guarantees_by_tool(tools, bindings, caps),
        },
        "collisions": collisions,
        "failure_modes": {
            "declared": bool(intent_summary.failure_modes) if intent_summary else False,
            "notes": intent_summary.failure_modes if intent_summary else None,
        },
        "issues": [issue.message for issue in issues],
        "status": status,
    }
    return PackReviewResult(status=status, payload=payload, issues=issues)


def _load_manifest(pack_dir: Path) -> PackManifest:
    manifest_path = pack_dir / "pack.yaml"
    try:
        return parse_pack_manifest(manifest_path)
    except Namel3ssError as err:
        raise Namel3ssError(
            build_guidance_message(
                what="Pack review failed.",
                why=str(err),
                fix="Fix pack.yaml and re-run review.",
                example="n3 packs validate --strict",
            )
        ) from err


def _load_bindings(pack_dir: Path, manifest: PackManifest) -> dict[str, ToolBinding]:
    bindings: dict[str, ToolBinding] = {}
    bindings_path = pack_bindings_path(pack_dir)
    if bindings_path.exists():
        text = bindings_path.read_text(encoding="utf-8")
        bindings = parse_bindings_yaml(text, bindings_path)
    elif manifest.entrypoints:
        bindings = dict(manifest.entrypoints)
    _apply_manifest_defaults(bindings, manifest)
    return bindings


def _apply_manifest_defaults(bindings: dict[str, ToolBinding], manifest: PackManifest) -> None:
    for name, binding in list(bindings.items()):
        runner = binding.runner or manifest.runners_default
        url = binding.url
        image = binding.image
        command = binding.command
        env = binding.env
        if runner == "service" and not url:
            url = manifest.service_url
        if runner == "container" and not image:
            image = manifest.container_image
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
        )


def _load_intent_summary(pack_dir: Path, validation: PackValidationResult):
    _ = validation
    try:
        text = load_intent(pack_dir)
    except Namel3ssError:
        return None
    return summarize_intent(text)


def _safe_capabilities(pack_dir: Path, validation: PackValidationResult) -> dict:
    _ = validation
    try:
        return load_pack_capabilities(pack_dir)
    except Namel3ssError:
        return {}


def _guarantees_by_tool(
    tools: list[str],
    bindings: dict[str, ToolBinding],
    caps: dict[str, object],
) -> dict[str, dict[str, object]]:
    results: dict[str, dict[str, object]] = {}
    for tool_name in tools:
        binding = bindings.get(tool_name)
        guarantees = build_effective_guarantees(
            tool_name=tool_name,
            tool_purity=None,
            binding_purity=binding.purity if binding else None,
            capabilities=caps.get(tool_name) if isinstance(caps, dict) else None,
            overrides=None,
            policy=None,
        )
        results[tool_name] = guarantees.to_dict()
    return results


def _find_collisions(tool_names: list[str], pack_id: str, app_root: Path | None) -> list[str]:
    collisions = set()
    builtin_tools = set(list_tool_pack_tools())
    for name in tool_names:
        if name in builtin_tools:
            collisions.add(name)
    if app_root is None:
        return sorted(collisions)
    config = read_pack_config(app_root)
    app = AppConfig()
    app.tool_packs = ToolPacksConfig(
        enabled_packs=config.enabled_packs,
        disabled_packs=config.disabled_packs,
        pinned_tools=config.pinned_tools,
    )
    registry = load_pack_registry(app_root, app)
    for name in tool_names:
        for item in registry.tools.get(name, []):
            if item.pack_id != pack_id:
                collisions.add(name)
    return sorted(collisions)


def _collision_issue(pack_id: str, tool_name: str) -> PackIssue:
    return PackIssue(
        "warning",
        build_guidance_message(
            what=f'Pack "{pack_id}" tool "{tool_name}" collides with another pack.',
            why="Tool names must be unique across packs to avoid conflicts.",
            fix="Rename the tool or disable the colliding pack.",
            example=f'n3 packs disable "{pack_id}"',
        ),
    )


def _status_from_issues(issues: list[PackIssue]) -> str:
    if any(issue.severity == "error" for issue in issues):
        return "fail"
    if any(issue.severity == "warning" for issue in issues):
        return "warn"
    return "ok"


__all__ = ["PackReviewResult", "review_pack"]
