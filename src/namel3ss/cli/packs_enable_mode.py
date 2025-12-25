from __future__ import annotations

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.config.loader import load_config
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.capabilities.effective import build_effective_guarantees, effective_capabilities_summary
from namel3ss.runtime.packs.ops import enable_pack
from namel3ss.runtime.packs.capabilities import load_pack_capabilities
from namel3ss.runtime.packs.layout import pack_manifest_path
from namel3ss.runtime.packs.manifest import parse_pack_manifest
from namel3ss.runtime.packs.policy import evaluate_policy, load_pack_policy, policy_denied_message
from namel3ss.runtime.packs.risk import risk_from_summary
from namel3ss.runtime.packs.runners import pack_runner_default
from namel3ss.runtime.packs.registry import load_pack_registry
from namel3ss.utils.json_tools import dumps_pretty


def run_packs_enable(args: list[str], *, json_mode: bool) -> int:
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
    if not pack.verified:
        raise Namel3ssError(_pack_unverified_message(pack_id))
    warning = None
    policy = load_pack_policy(app_root)
    policy_summary = _pack_effective_summary(pack, config, None)
    summary = _pack_effective_summary(pack, config, policy) or policy_summary
    runner_default = _pack_runner_default(pack)
    risk = risk_from_summary(summary, runner_default)
    decision = evaluate_policy(
        policy,
        operation="enable",
        verified=pack.verified,
        risk=risk,
        capabilities=_flatten_capabilities(policy_summary),
    )
    if policy.source_path and not decision.allowed:
        raise Namel3ssError(policy_denied_message(pack_id, "enable", decision.reasons))
    if policy.source_path is None and risk != "low":
        warning = "Pack capabilities are elevated. Add .namel3ss/trust/policy.toml to enforce capability limits."
    path = enable_pack(app_root, pack_id)
    payload = {"status": "ok", "pack_id": pack_id, "config_path": str(path)}
    if warning:
        payload["warning"] = warning
    if json_mode:
        print(dumps_pretty(payload))
        return 0
    if warning:
        print(f"Warning: {warning}")
    print(f"Enabled pack '{pack_id}'.")
    return 0


def _missing_pack_message() -> str:
    return build_guidance_message(
        what="Pack id is missing.",
        why="You must specify which pack to enable.",
        fix="Provide a pack id.",
        example="n3 packs enable pack.slug",
    )


def _unknown_args_message(args: list[str]) -> str:
    joined = " ".join(args)
    return build_guidance_message(
        what=f"Unknown arguments: {joined}.",
        why="n3 packs enable accepts a pack id only.",
        fix="Remove the extra arguments.",
        example="n3 packs enable pack.slug",
    )


def _pack_missing_message(pack_id: str) -> str:
    return build_guidance_message(
        what=f'Pack "{pack_id}" was not found.',
        why="The pack is not installed.",
        fix="Install the pack before enabling it.",
        example=f"n3 packs add ./packs/{pack_id}",
    )


def _pack_unverified_message(pack_id: str) -> str:
    return build_guidance_message(
        what=f'Pack "{pack_id}" is unverified.',
        why="Unverified packs cannot be enabled by default.",
        fix="Verify the pack before enabling it.",
        example=f"n3 packs verify {pack_id}",
    )


def _pack_effective_summary(pack, config, policy) -> dict[str, object]:
    if not pack.pack_root:
        return {"levels": {"filesystem": "none", "network": "none", "env": "none", "subprocess": "none"}, "secrets": []}
    try:
        caps = load_pack_capabilities(pack.pack_root)
    except Namel3ssError:
        return {"levels": {"filesystem": "none", "network": "none", "env": "none", "subprocess": "none"}, "secrets": []}
    if not caps:
        return {"levels": {"filesystem": "none", "network": "none", "env": "none", "subprocess": "none"}, "secrets": []}
    summaries = []
    for tool_name in pack.tools:
        binding = pack.bindings.get(tool_name)
        guarantees = build_effective_guarantees(
            tool_name=tool_name,
            tool_purity=None,
            binding_purity=binding.purity if binding else None,
            capabilities=caps.get(tool_name),
            overrides=config.capability_overrides.get(tool_name),
            policy=policy,
        )
        summaries.append(effective_capabilities_summary(caps.get(tool_name), guarantees))
    return _aggregate_effective_summaries(summaries)


def _pack_runner_default(pack) -> str | None:
    if not pack.pack_root:
        return None
    manifest = parse_pack_manifest(pack_manifest_path(pack.pack_root))
    return pack_runner_default(manifest, pack.bindings)


def _flatten_capabilities(summary: dict[str, object]) -> dict[str, object]:
    levels = summary.get("levels") if isinstance(summary, dict) else {}
    if not isinstance(levels, dict):
        levels = {}
    return {
        "filesystem": str(levels.get("filesystem", "none")),
        "network": str(levels.get("network", "none")),
        "env": str(levels.get("env", "none")),
        "subprocess": str(levels.get("subprocess", "none")),
        "secrets": list(summary.get("secrets", [])) if isinstance(summary, dict) else [],
    }


def _aggregate_effective_summaries(summaries: list[dict[str, object]]) -> dict[str, object]:
    if not summaries:
        return {"levels": {"filesystem": "none", "network": "none", "env": "none", "subprocess": "none"}, "secrets": []}
    order = {
        "filesystem": ["none", "read", "write", "unknown"],
        "network": ["none", "outbound", "unknown"],
        "env": ["none", "read", "unknown"],
        "subprocess": ["none", "allow", "unknown"],
    }
    levels = {key: "none" for key in order}
    secrets: set[str] = set()
    for summary in summaries:
        level_map = summary.get("levels") if isinstance(summary, dict) else {}
        if not isinstance(level_map, dict):
            level_map = {}
        for key in order:
            current = levels.get(key, "none")
            candidate = str(level_map.get(key, current))
            levels[key] = _max_level(current, candidate, order[key])
        secret_list = summary.get("secrets") if isinstance(summary, dict) else []
        if isinstance(secret_list, list):
            secrets.update(secret_list)
    return {"levels": levels, "secrets": sorted(secrets)}


def _max_level(current: str, candidate: str, order: list[str]) -> str:
    if current not in order:
        current = "unknown"
    if candidate not in order:
        candidate = "unknown"
    if order.index(candidate) >= order.index(current):
        return candidate
    return current


__all__ = ["run_packs_enable"]
