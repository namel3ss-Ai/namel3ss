from __future__ import annotations

from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.governance.verify_types import VerifyCheck
from namel3ss.runtime.capabilities.effective import (
    build_effective_guarantees,
    effective_capabilities_summary,
    summarize_guarantees,
)
from namel3ss.runtime.capabilities.report import collect_tool_reports
from namel3ss.runtime.packs.capabilities import capabilities_summary, load_pack_capabilities
from namel3ss.runtime.packs.layout import pack_manifest_path
from namel3ss.runtime.packs.manifest import parse_pack_manifest
from namel3ss.runtime.packs.policy import evaluate_policy, load_pack_policy
from namel3ss.runtime.packs.registry import load_pack_registry
from namel3ss.runtime.packs.risk import risk_from_summary
from namel3ss.runtime.packs.runners import pack_runner_default


def check_pack_capabilities(project_root: Path, config, prod: bool) -> VerifyCheck:
    policy = load_pack_policy(project_root)
    registry = load_pack_registry(project_root, config)
    installed = [
        pack for pack in registry.packs.values() if pack.source == "installed_pack" and pack.enabled and pack.verified
    ]
    if not installed:
        return VerifyCheck(
            id="pack_capabilities",
            status="ok",
            message="No enabled installed packs.",
            fix="None.",
        )
    summaries = []
    missing = []
    unsafe = []
    policy_blocked: list[dict[str, object]] = []
    for pack in installed:
        if not pack.pack_root:
            continue
        try:
            capabilities = load_pack_capabilities(pack.pack_root)
        except Namel3ssError:
            missing.append(pack.pack_id)
            continue
        if not capabilities:
            missing.append(pack.pack_id)
            continue
        summary = capabilities_summary(capabilities)
        guarantees_summary = summarize_guarantees(capabilities)
        policy_summary = _effective_pack_summary(pack, capabilities, config, None)
        effective_summary = _effective_pack_summary(pack, capabilities, config, policy)
        runner_default = _pack_runner_default(pack)
        risk = risk_from_summary(effective_summary or summary, runner_default)
        summaries.append(
            {
                "pack_id": pack.pack_id,
                "summary": summary,
                "guarantees": guarantees_summary,
                "effective_summary": effective_summary,
            }
        )
        if _capabilities_unsafe(effective_summary or summary):
            unsafe.append(pack.pack_id)
        decision = evaluate_policy(
            policy,
            operation="enable",
            verified=pack.verified,
            risk=risk,
            capabilities=_flatten_capabilities(policy_summary or summary),
        )
        if policy.source_path and not decision.allowed:
            policy_blocked.append({"pack_id": pack.pack_id, "reasons": decision.reasons, "risk": risk})
    status = "ok"
    message = "Pack capabilities are within the declared baseline."
    fix = "None."
    if unsafe or missing:
        status = "warn" if prod else "warn"
        message = "Pack capabilities include elevated access or missing declarations."
        fix = "Review pack capabilities and disable or update unsafe packs."
    if policy_blocked:
        status = "fail" if prod else "warn"
        message = "Pack capabilities violate trust policy."
        fix = "Update policy or disable the blocked packs."
    details = {
        "unsafe_packs": sorted(unsafe),
        "missing_capabilities": sorted(missing),
        "summaries": summaries,
        "policy_blocked": policy_blocked,
    }
    return VerifyCheck(id="pack_capabilities", status=status, message=message, fix=fix, details=details)


def check_tool_guarantees(
    project_root: Path,
    config,
    tools: dict[str, object],
    prod: bool,
    *,
    allow_unsafe: bool,
) -> VerifyCheck:
    reports = collect_tool_reports(project_root, config, tools)
    blocked = [entry for entry in reports if entry.get("blocked")]
    missing_sandbox: list[str] = []
    service_handshake_missing: list[str] = []
    container_unverified: list[str] = []
    unsafe_overrides: list[str] = []
    handshake_required = config.python_tools.service_handshake_required is True
    for entry in reports:
        tool_name = entry.get("tool_name")
        if not isinstance(tool_name, str):
            continue
        if entry.get("unsafe_override"):
            unsafe_overrides.append(tool_name)
        runner = entry.get("runner")
        if runner == "local":
            pure = getattr(tools.get(tool_name), "purity", None) == "pure"
            sandbox_on = bool((entry.get("sandbox") or {}).get("enabled"))
            if not sandbox_on and not pure:
                missing_sandbox.append(tool_name)
        if runner == "service" and prod and not handshake_required:
            service_handshake_missing.append(tool_name)
        if runner == "container" and prod:
            coverage = entry.get("coverage") or {}
            enforcement = coverage.get("container_enforcement")
            if enforcement != "verified":
                container_unverified.append(tool_name)
    status = "ok"
    message = "Tool guarantees are enforceable."
    fix = "None."
    if blocked or missing_sandbox or service_handshake_missing or container_unverified:
        status = "fail" if prod else "warn"
        message = "Tool enforcement coverage requires attention."
        fix = "Switch runners, enable sandbox, or update enforcement declarations."
    if unsafe_overrides and prod and not allow_unsafe:
        status = "fail"
        message = "Unsafe overrides are present."
        fix = "Remove allow_unsafe_execution overrides or rerun verify with --allow-unsafe."
    details = {
        "blocked_tools": sorted(entry.get("tool_name") for entry in blocked if entry.get("tool_name")),
        "reports": reports,
        "missing_sandbox": sorted(set(missing_sandbox)),
        "service_handshake_required": handshake_required,
        "service_handshake_missing": sorted(set(service_handshake_missing)),
        "container_enforcement_missing": sorted(set(container_unverified)),
        "unsafe_overrides": sorted(set(unsafe_overrides)),
    }
    return VerifyCheck(id="tool_guarantees", status=status, message=message, fix=fix, details=details)


def _pack_runner_default(pack) -> str | None:
    if not pack.pack_root:
        return None
    manifest = parse_pack_manifest(pack_manifest_path(pack.pack_root))
    return pack_runner_default(manifest, pack.bindings)


def _effective_pack_summary(pack, capabilities, config, policy) -> dict[str, object]:
    summaries: list[dict[str, object]] = []
    for tool_name in pack.tools:
        binding = pack.bindings.get(tool_name)
        guarantees = build_effective_guarantees(
            tool_name=tool_name,
            tool_purity=None,
            binding_purity=binding.purity if binding else None,
            capabilities=capabilities.get(tool_name),
            overrides=config.capability_overrides.get(tool_name),
            policy=policy,
        )
        summaries.append(effective_capabilities_summary(capabilities.get(tool_name), guarantees))
    return _aggregate_effective_summaries(summaries)


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


def _capabilities_unsafe(summary: dict) -> bool:
    levels = summary.get("levels") or {}
    secrets = summary.get("secrets") or []
    for key in ("filesystem", "network", "env", "subprocess"):
        if levels.get(key) not in {None, "none"}:
            return True
    return bool(secrets)


__all__ = ["check_pack_capabilities", "check_tool_guarantees"]
