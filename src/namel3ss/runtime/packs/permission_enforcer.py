from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from namel3ss.runtime.capabilities.builtin import get_builtin_tool_capabilities
from namel3ss.runtime.packs.capabilities import ToolCapabilities, capabilities_summary, load_pack_capabilities
from namel3ss.runtime.packs.layout import pack_manifest_path
from namel3ss.runtime.packs.manifest import parse_pack_manifest
from namel3ss.runtime.packs.policy import PackTrustPolicy, evaluate_policy, load_pack_policy
from namel3ss.runtime.packs.risk import risk_from_summary
from namel3ss.runtime.packs.runners import pack_runner_default


@dataclass(frozen=True)
class PackPermissionDecision:
    pack_id: str
    allowed: bool
    reasons: list[str]
    summary: dict[str, object]
    risk: str
    policy_source: str | None


def evaluate_pack_permission(
    pack,
    *,
    app_root: Path | None,
    policy: PackTrustPolicy | None = None,
) -> PackPermissionDecision:
    capabilities = _pack_capabilities(pack)
    summary = capabilities_summary(capabilities)
    runner_default = _pack_runner_default(pack)
    risk = risk_from_summary(summary, runner_default)
    policy = policy if policy is not None else (load_pack_policy(app_root) if app_root else None)
    if policy is None or policy.source_path is None:
        return PackPermissionDecision(
            pack_id=pack.pack_id,
            allowed=True,
            reasons=[],
            summary=summary,
            risk=risk,
            policy_source=None,
        )
    decision = evaluate_policy(
        policy,
        operation="enable",
        verified=bool(pack.verified),
        risk=risk,
        capabilities=_flatten_capabilities(summary),
    )
    return PackPermissionDecision(
        pack_id=pack.pack_id,
        allowed=decision.allowed,
        reasons=list(decision.reasons),
        summary=summary,
        risk=risk,
        policy_source=_normalize_policy_source(policy.source_path, app_root),
    )


def _pack_capabilities(pack) -> dict[str, ToolCapabilities]:
    if pack.source == "builtin_pack":
        return _builtin_pack_capabilities(pack.tools)
    if pack.pack_root:
        try:
            raw = load_pack_capabilities(pack.pack_root)
        except Exception:
            raw = {}
        return _normalize_pack_capabilities(pack.tools, raw)
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


def _pack_runner_default(pack) -> str | None:
    if not pack.pack_root:
        return None
    try:
        manifest = parse_pack_manifest(pack_manifest_path(pack.pack_root))
    except Exception:
        return None
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


def _normalize_policy_source(source: Path | None, app_root: Path | None) -> str | None:
    if source is None:
        return None
    try:
        path = source if isinstance(source, Path) else Path(str(source))
    except Exception:
        return None
    if app_root is not None:
        try:
            relative = path.resolve().relative_to(app_root.resolve())
            return relative.as_posix()
        except Exception:
            pass
    return path.name or None


__all__ = ["PackPermissionDecision", "evaluate_pack_permission"]
