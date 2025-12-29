from __future__ import annotations

from pathlib import Path

from namel3ss.config.model import AppConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.capabilities.coverage import (
    container_runner_coverage,
    local_runner_coverage,
    service_runner_coverage,
)
from namel3ss.runtime.capabilities.effective import build_effective_guarantees, resolve_tool_capabilities
from namel3ss.runtime.capabilities.overrides import unsafe_override_enabled
from namel3ss.runtime.packs.policy import load_pack_policy
from namel3ss.runtime.tools.resolution import resolve_tool_binding
from namel3ss.runtime.tools.sandbox import sandbox_enabled


def collect_tool_reports(
    app_root: Path,
    config: AppConfig,
    tools: dict[str, object],
) -> list[dict[str, object]]:
    reports: list[dict[str, object]] = []
    for tool_name in sorted(tools.keys()):
        tool_decl = tools[tool_name]
        try:
            resolved = resolve_tool_binding(
                app_root,
                tool_name,
                config,
                tool_kind=getattr(tool_decl, "kind", None),
                line=None,
                column=None,
            )
            binding = resolved.binding
            runner_name = binding.runner or "local"
            pack_root = _pack_root_from_paths(resolved.pack_paths)
            policy = load_pack_policy(app_root) if resolved.source in {"builtin_pack", "installed_pack"} else None
            overrides = config.capability_overrides.get(tool_name)
            unsafe_override = unsafe_override_enabled(overrides)
            handshake_required = _handshake_required(config)
            guarantees = build_effective_guarantees(
                tool_name=tool_name,
                tool_purity=getattr(tool_decl, "purity", None),
                binding_purity=binding.purity,
                capabilities=resolve_tool_capabilities(tool_name, resolved.source, pack_root),
                overrides=overrides,
                policy=policy,
            )
            coverage = _coverage_for(
                guarantees,
                runner_name,
                binding=binding,
                resolved_source=resolved.source,
                handshake_required=handshake_required,
            )
            blocked = _is_blocked(coverage, runner_name, binding, unsafe_override, handshake_required)
            report = {
                "tool_name": tool_name,
                "resolved_source": resolved.source,
                "runner": runner_name,
                "guarantees": guarantees.to_dict(),
                "guarantee_sources": dict(guarantees.sources),
                "coverage": coverage,
                "sandbox": {"enabled": sandbox_enabled(resolved_source=resolved.source, runner=runner_name, binding=binding)},
                "unsafe_override": unsafe_override,
                "blocked": blocked,
            }
            if blocked:
                report["blocked_reason"] = _blocked_reason(coverage, runner_name, binding, unsafe_override)
            reports.append(report)
        except Namel3ssError as err:
            reports.append(
                {
                    "tool_name": tool_name,
                    "resolved_source": None,
                    "runner": None,
                    "guarantees": {},
                    "guarantee_sources": {},
                    "coverage": {"status": "unknown", "missing": []},
                    "sandbox": {"enabled": False},
                    "unsafe_override": False,
                    "blocked": True,
                    "blocked_reason": str(err),
                }
            )
    return reports


def _pack_root_from_paths(paths: list[Path] | None) -> Path | None:
    if not paths:
        return None
    return paths[0]


def _coverage_for(guarantees, runner: str, *, binding, resolved_source: str, handshake_required: bool) -> dict[str, object]:
    if runner in {"local", "node"}:
        coverage = local_runner_coverage(
            guarantees,
            sandbox_enabled=sandbox_enabled(resolved_source=resolved_source, runner=runner, binding=binding),
        )
        return {"status": coverage.status, "missing": coverage.missing}
    if runner == "service":
        coverage = service_runner_coverage(guarantees, enforcement_level=None, handshake_required=handshake_required)
        return {
            "status": coverage.status,
            "missing": coverage.missing,
            "service_handshake": "required" if handshake_required else "disabled",
        }
    if runner == "container":
        coverage = container_runner_coverage(guarantees, enforcement=binding.enforcement)
        return {
            "status": coverage.status,
            "missing": coverage.missing,
            "container_enforcement": binding.enforcement,
        }
    return {"status": "unknown", "missing": []}


def _handshake_required(config: AppConfig) -> bool:
    required = getattr(config.python_tools, "service_handshake_required", None)
    return bool(required)


def _is_blocked(
    coverage: dict[str, object],
    runner: str,
    binding,
    unsafe_override: bool,
    handshake_required: bool,
) -> bool:
    status = str(coverage.get("status") or "unknown")
    if status == "enforced":
        return False
    if unsafe_override:
        return False
    if runner == "service" and not handshake_required:
        return False
    if runner == "container" and binding.enforcement == "declared" and status == "partially_enforced":
        return False
    return True


def _blocked_reason(
    coverage: dict[str, object],
    runner: str,
    binding,
    unsafe_override: bool,
) -> str:
    status = str(coverage.get("status") or "unknown")
    missing = coverage.get("missing") or []
    missing_list = ", ".join(missing) if missing else "unspecified"
    if unsafe_override:
        return "unsafe override enabled"
    if runner == "container" and "subprocess" in missing:
        return "container runner requires subprocess access"
    if runner == "local":
        return f"sandbox required to enforce: {missing_list}"
    if runner == "service":
        return f"service enforcement missing: {missing_list}"
    if runner == "container":
        if binding.enforcement is None:
            return "container enforcement not declared"
        return f"container enforcement {binding.enforcement}"
    return f"coverage status {status}"


__all__ = ["collect_tool_reports"]
