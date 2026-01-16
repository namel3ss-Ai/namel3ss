from __future__ import annotations

from namel3ss.config.model import AppConfig


def foreign_policy_mode(config: AppConfig | None) -> str:
    if config is None:
        return "default"
    foreign = getattr(config, "foreign", None)
    if foreign and foreign.strict:
        return "strict"
    return "default"


def foreign_policy_allows(config: AppConfig | None) -> bool:
    if config is None:
        return True
    foreign = getattr(config, "foreign", None)
    if not foreign:
        return True
    if foreign.strict and not foreign.allow:
        return False
    return True


__all__ = ["foreign_policy_allows", "foreign_policy_mode"]
