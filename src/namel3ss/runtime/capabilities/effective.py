from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from namel3ss.runtime.capabilities.model import EffectiveGuarantees, GUARANTEE_FIELDS
from namel3ss.runtime.capabilities.validate import normalize_overrides
from namel3ss.runtime.packs.capabilities import ToolCapabilities, load_pack_capabilities
from namel3ss.runtime.packs.policy import PackTrustPolicy
from namel3ss.runtime.capabilities.builtin import get_builtin_tool_capabilities


@dataclass
class _GuaranteeBuilder:
    values: dict[str, bool]
    sources: dict[str, str]
    secrets_allowed: list[str] | None = None

    @classmethod
    def start(cls) -> "_GuaranteeBuilder":
        return cls(values={key: False for key in GUARANTEE_FIELDS}, sources={})

    def apply(self, source: str, values: dict[str, bool], secrets: list[str] | None) -> None:
        for key, value in values.items():
            if value:
                self.values[key] = True
                self.sources[key] = source
        if secrets is not None:
            normalized = sorted(dict.fromkeys(secrets))
            if self.secrets_allowed is None:
                self.secrets_allowed = normalized
                self.sources["secrets_allowed"] = source
            else:
                merged = sorted(set(self.secrets_allowed) & set(normalized))
                if merged != self.secrets_allowed:
                    self.secrets_allowed = merged
                    self.sources["secrets_allowed"] = source

    def build(self) -> EffectiveGuarantees:
        return EffectiveGuarantees(
            no_filesystem_write=self.values["no_filesystem_write"],
            no_filesystem_read=self.values["no_filesystem_read"],
            no_network=self.values["no_network"],
            no_subprocess=self.values["no_subprocess"],
            no_env_read=self.values["no_env_read"],
            no_env_write=self.values["no_env_write"],
            secrets_allowed=self.secrets_allowed,
            sources=dict(self.sources),
        )


def build_effective_guarantees(
    *,
    tool_name: str,
    tool_purity: str | None,
    binding_purity: str | None,
    capabilities: ToolCapabilities | None,
    overrides: object | None,
    policy: PackTrustPolicy | None,
) -> EffectiveGuarantees:
    builder = _GuaranteeBuilder.start()
    caps_values, caps_secrets = _guarantees_from_capabilities(capabilities)
    builder.apply("pack", caps_values, caps_secrets)

    purity = binding_purity or tool_purity
    purity_values, purity_secrets = _guarantees_from_purity(purity)
    builder.apply("tool", purity_values, purity_secrets)

    if overrides is not None:
        normalized = normalize_overrides(overrides, label=f'"{tool_name}"')
        override_values, override_secrets = _guarantees_from_overrides(normalized)
        builder.apply("user", override_values, override_secrets)

    policy_values, policy_secrets = _guarantees_from_policy(policy)
    builder.apply("policy", policy_values, policy_secrets)
    return builder.build()


def resolve_tool_capabilities(
    tool_name: str,
    resolved_source: str,
    pack_root: Path | None,
) -> ToolCapabilities | None:
    if resolved_source == "builtin_pack":
        return get_builtin_tool_capabilities(tool_name)
    if resolved_source == "installed_pack" and pack_root:
        capabilities = load_pack_capabilities(pack_root)
        return capabilities.get(tool_name)
    return None


def summarize_guarantees(capabilities: dict[str, ToolCapabilities]) -> dict[str, object]:
    if not capabilities:
        return {}
    summaries: list[dict[str, object]] = []
    secrets: set[str] = set()
    for cap in capabilities.values():
        values, cap_secrets = _guarantees_from_capabilities(cap)
        summaries.append(values)
        secrets.update(cap_secrets or [])
    merged = {key: all(item.get(key, False) for item in summaries) for key in GUARANTEE_FIELDS}
    payload: dict[str, object] = dict(merged)
    payload["secrets_allowed"] = sorted(secrets)
    return payload


def effective_capabilities_summary(
    capabilities: ToolCapabilities | None,
    guarantees: EffectiveGuarantees,
) -> dict[str, object]:
    base = capabilities
    levels = {
        "filesystem": base.filesystem if base else "unknown",
        "network": base.network if base else "unknown",
        "env": base.env if base else "unknown",
        "subprocess": base.subprocess if base else "unknown",
    }
    if guarantees.no_filesystem_read:
        levels["filesystem"] = "none"
    elif guarantees.no_filesystem_write and levels["filesystem"] == "write":
        levels["filesystem"] = "read"
    if guarantees.no_network:
        levels["network"] = "none"
    if guarantees.no_env_read:
        levels["env"] = "none"
    if guarantees.no_subprocess:
        levels["subprocess"] = "none"
    secrets = guarantees.secrets_allowed if guarantees.secrets_allowed is not None else list(base.secrets) if base else []
    return {"levels": levels, "secrets": list(secrets)}


def _guarantees_from_capabilities(capabilities: ToolCapabilities | None) -> tuple[dict[str, bool], list[str] | None]:
    if capabilities is None:
        return {}, None
    filesystem = capabilities.filesystem
    network = capabilities.network
    env = capabilities.env
    subprocess = capabilities.subprocess
    values = {
        "no_filesystem_write": filesystem in {"none", "read"},
        "no_filesystem_read": filesystem == "none",
        "no_network": network == "none",
        "no_subprocess": subprocess == "none",
        "no_env_read": env == "none",
        "no_env_write": env in {"none", "read"},
    }
    return values, list(capabilities.secrets)


def _guarantees_from_purity(purity: str | None) -> tuple[dict[str, bool], list[str] | None]:
    if purity != "pure":
        return {}, None
    values = {
        "no_filesystem_write": True,
        "no_filesystem_read": True,
        "no_network": True,
        "no_subprocess": True,
        "no_env_read": True,
        "no_env_write": True,
    }
    return values, []


def _guarantees_from_overrides(overrides: dict[str, object]) -> tuple[dict[str, bool], list[str] | None]:
    values: dict[str, bool] = {}
    secrets_allowed: list[str] | None = None
    for key, value in overrides.items():
        if key == "secrets_allowed":
            secrets_allowed = list(value) if isinstance(value, list) else []
            continue
        if key in GUARANTEE_FIELDS and isinstance(value, bool):
            values[key] = value
    return values, secrets_allowed


def _guarantees_from_policy(policy: PackTrustPolicy | None) -> tuple[dict[str, bool], list[str] | None]:
    if policy is None or policy.source_path is None:
        return {}, None
    allowed = policy.allowed_capabilities
    values = {
        "no_filesystem_write": allowed.get("filesystem") in {"none", "read"},
        "no_filesystem_read": allowed.get("filesystem") == "none",
        "no_network": allowed.get("network") == "none",
        "no_subprocess": allowed.get("subprocess") == "none",
        "no_env_read": allowed.get("env") == "none",
        "no_env_write": allowed.get("env") in {"none", "read"},
    }
    return values, None


__all__ = [
    "build_effective_guarantees",
    "effective_capabilities_summary",
    "resolve_tool_capabilities",
    "summarize_guarantees",
]
