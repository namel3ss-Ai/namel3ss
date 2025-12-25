from __future__ import annotations

from dataclasses import dataclass

from namel3ss.runtime.capabilities.model import EffectiveGuarantees


@dataclass(frozen=True)
class CoverageResult:
    status: str
    missing: list[str]


def required_capabilities(guarantees: EffectiveGuarantees) -> list[str]:
    required: list[str] = []
    if guarantees.no_filesystem_read:
        required.append("filesystem_read")
    if guarantees.no_filesystem_write:
        required.append("filesystem_write")
    if guarantees.no_network:
        required.append("network")
    if guarantees.no_subprocess:
        required.append("subprocess")
    if guarantees.no_env_read:
        required.append("env_read")
    if guarantees.no_env_write:
        required.append("env_write")
    if guarantees.secrets_allowed is not None:
        required.append("secrets")
    return required


def local_runner_coverage(guarantees: EffectiveGuarantees, *, sandbox_enabled: bool) -> CoverageResult:
    required = required_capabilities(guarantees)
    if not required:
        return CoverageResult(status="enforced", missing=[])
    if sandbox_enabled:
        return CoverageResult(status="enforced", missing=[])
    return CoverageResult(status="not_enforceable", missing=required)


def service_runner_coverage(
    guarantees: EffectiveGuarantees,
    *,
    enforcement_level: str | None,
    handshake_required: bool,
) -> CoverageResult:
    required = required_capabilities(guarantees)
    if not required:
        return CoverageResult(status="enforced", missing=[])
    if enforcement_level == "enforced":
        return CoverageResult(status="enforced", missing=[])
    if enforcement_level == "partial":
        return CoverageResult(status="partially_enforced", missing=required)
    if enforcement_level == "none":
        return CoverageResult(status="not_enforceable", missing=required)
    if handshake_required:
        return CoverageResult(status="not_enforceable", missing=required)
    return CoverageResult(status="partially_enforced", missing=required)


def container_runner_coverage(
    guarantees: EffectiveGuarantees,
    *,
    enforcement: str | None,
) -> CoverageResult:
    required = required_capabilities(guarantees)
    if not required:
        return CoverageResult(status="enforced", missing=[])
    if guarantees.no_subprocess:
        return CoverageResult(status="not_enforceable", missing=["subprocess"])
    if enforcement == "verified":
        return CoverageResult(status="enforced", missing=[])
    if enforcement == "declared":
        return CoverageResult(status="partially_enforced", missing=required)
    return CoverageResult(status="not_enforceable", missing=required)


__all__ = [
    "CoverageResult",
    "container_runner_coverage",
    "local_runner_coverage",
    "required_capabilities",
    "service_runner_coverage",
]
