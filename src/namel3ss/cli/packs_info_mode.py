from __future__ import annotations

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.config.loader import load_config
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.capabilities.builtin import get_builtin_tool_capabilities
from namel3ss.runtime.packs.capabilities import ToolCapabilities, capabilities_by_tool, capabilities_summary, load_pack_capabilities
from namel3ss.runtime.packs.permission_enforcer import evaluate_pack_permission
from namel3ss.runtime.packs.policy import load_pack_policy
from namel3ss.runtime.packs.registry import load_pack_registry, pack_payload
from namel3ss.utils.json_tools import dumps_pretty


def run_packs_info(args: list[str], *, json_mode: bool) -> int:
    if not args:
        raise Namel3ssError(_missing_pack_message())
    pack_id = args[0]
    if len(args) > 1:
        raise Namel3ssError(_unknown_args_message(args[1:]))
    app_path = resolve_app_path(None)
    app_root = app_path.parent
    config = load_config(root=app_root)
    registry = load_pack_registry(app_root, config)
    pack = registry.packs.get(pack_id)
    if not pack:
        raise Namel3ssError(_pack_missing_message(pack_id))
    capabilities = _pack_capabilities(pack)
    summary = capabilities_summary(capabilities)
    policy = load_pack_policy(app_root)
    decision = evaluate_pack_permission(pack, app_root=app_root, policy=policy)
    payload = pack_payload(pack)
    payload["capabilities"] = capabilities_by_tool(capabilities)
    payload["capabilities_summary"] = summary
    payload["permission"] = {
        "allowed": decision.allowed,
        "reasons": list(decision.reasons),
        "risk": decision.risk,
        "policy_source": decision.policy_source,
    }
    if json_mode:
        print(dumps_pretty(payload))
        return 0
    print(f"Pack: {pack.pack_id}")
    print(f"Name: {pack.name}")
    if pack.version:
        print(f"Version: {pack.version}")
    source = _source_label(pack.source)
    print(f"Source: {source}")
    status = "enabled" if pack.enabled else "disabled"
    verify = "verified" if pack.verified else "unverified"
    print(f"Status: {status}, {verify}")
    if pack.tools:
        print("Tools:")
        for tool_name in sorted(pack.tools):
            print(f"- {tool_name}")
    _print_summary(summary)
    _print_permission(decision)
    if pack.errors:
        print("Errors:")
        for err in pack.errors:
            print(f"- {err}")
    return 0


def _missing_pack_message() -> str:
    return build_guidance_message(
        what="Pack id is missing.",
        why="You must specify which pack to inspect.",
        fix="Provide a pack id.",
        example="n3 pack info builtin.text",
    )


def _unknown_args_message(args: list[str]) -> str:
    joined = " ".join(args)
    return build_guidance_message(
        what=f"Unknown arguments: {joined}.",
        why="n3 pack info accepts a pack id only.",
        fix="Remove the extra arguments.",
        example="n3 pack info builtin.text",
    )


def _pack_missing_message(pack_id: str) -> str:
    return build_guidance_message(
        what=f'Pack "{pack_id}" was not found.',
        why="The pack is not available in this project.",
        fix="Add a local pack or install the pack first.",
        example=f"n3 pack info {pack_id}",
    )


def _source_label(source: str) -> str:
    if source == "builtin_pack":
        return "builtin"
    if source == "installed_pack":
        return "installed"
    if source == "local_pack":
        return "local"
    return source


def _print_summary(summary: dict[str, object]) -> None:
    levels = summary.get("levels") if isinstance(summary, dict) else {}
    if not isinstance(levels, dict):
        return
    secrets = summary.get("secrets") if isinstance(summary, dict) else []
    secret_count = len(secrets) if isinstance(secrets, list) else 0
    print(
        "Capabilities summary: "
        f'fs={levels.get("filesystem", "none")},'
        f'net={levels.get("network", "none")},'
        f'env={levels.get("env", "none")},'
        f'sub={levels.get("subprocess", "none")},'
        f"secrets={secret_count}"
    )


def _print_permission(decision) -> None:
    if decision.policy_source:
        status = "allowed" if decision.allowed else "blocked"
        print(f"Policy: {status}")
        for reason in decision.reasons:
            print(f"- {reason}")


def _pack_capabilities(pack) -> dict[str, ToolCapabilities]:
    if pack.source == "builtin_pack":
        return _builtin_pack_capabilities(pack.tools)
    if pack.pack_root:
        try:
            capabilities = load_pack_capabilities(pack.pack_root)
        except Namel3ssError:
            capabilities = {}
        return _normalize_pack_capabilities(pack.tools, capabilities)
    return {}


def _builtin_pack_capabilities(tools: list[str]) -> dict[str, ToolCapabilities]:
    capabilities: dict[str, ToolCapabilities] = {}
    for tool_name in tools:
        cap = get_builtin_tool_capabilities(tool_name) or _default_capabilities()
        capabilities[tool_name] = cap
    return capabilities


def _normalize_pack_capabilities(
    tools: list[str],
    raw: dict[str, ToolCapabilities],
) -> dict[str, ToolCapabilities]:
    capabilities: dict[str, ToolCapabilities] = {}
    for tool_name in tools:
        cap = raw.get(tool_name) if isinstance(raw, dict) else None
        capabilities[tool_name] = cap if cap is not None else _default_capabilities()
    return capabilities


def _default_capabilities() -> ToolCapabilities:
    return ToolCapabilities(
        filesystem="none",
        network="none",
        env="none",
        subprocess="none",
        secrets=[],
    )


__all__ = ["run_packs_info"]
