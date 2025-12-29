from __future__ import annotations

from dataclasses import dataclass

from namel3ss.config.model import AppConfig

CAPABILITIES = (
    "network",
    "filesystem_read",
    "filesystem_write",
    "subprocess",
    "secrets",
)

_CAPABILITY_TO_OVERRIDE = {
    "network": "no_network",
    "filesystem_read": "no_filesystem_read",
    "filesystem_write": "no_filesystem_write",
    "subprocess": "no_subprocess",
    "secrets": "secrets_allowed",
}


@dataclass(frozen=True)
class ToolPolicy:
    denied_capabilities: tuple[str, ...]
    known_tool: bool
    binding_ok: bool


def normalize_capabilities(values: tuple[str, ...] | list[str] | None) -> tuple[str, ...]:
    if not values:
        return ()
    normalized = {str(item) for item in values if isinstance(item, str) and item in CAPABILITIES}
    return tuple(sorted(normalized))


def load_tool_policy(
    *,
    tool_name: str,
    tool_known: bool,
    binding_ok: bool,
    config: AppConfig | None,
) -> ToolPolicy:
    overrides = {}
    if config is not None:
        overrides = getattr(config, "capability_overrides", {}).get(tool_name, {}) or {}
    denied: set[str] = set()
    for capability, override_key in _CAPABILITY_TO_OVERRIDE.items():
        if override_key == "secrets_allowed":
            secrets = overrides.get(override_key)
            if isinstance(secrets, list) and not secrets:
                denied.add(capability)
            continue
        if overrides.get(override_key) is True:
            denied.add(capability)
    return ToolPolicy(
        denied_capabilities=tuple(sorted(denied)),
        known_tool=tool_known,
        binding_ok=binding_ok,
    )


__all__ = ["CAPABILITIES", "ToolPolicy", "load_tool_policy", "normalize_capabilities"]
