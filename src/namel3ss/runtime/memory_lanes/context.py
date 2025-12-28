from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping
from hashlib import sha256
from pathlib import Path


@dataclass(frozen=True)
class LaneContext:
    team_id: str


@dataclass(frozen=True)
class SystemRuleRequest:
    text: str
    reason: str


def resolve_team_id(*, project_root: str | None, app_path: str | None, config: object | None = None) -> str:
    if config is not None:
        value = _team_id_from_config(config)
        if value:
            return value
    seed = project_root or app_path
    if not seed:
        return "unknown"
    normalized = _normalize_path(seed)
    digest = sha256(normalized.encode("utf-8")).hexdigest()
    return digest[:12]


def system_rule_request_from_state(state: Mapping[str, object] | None) -> SystemRuleRequest | None:
    if not isinstance(state, dict):
        return None
    text = state.get("_memory_system_rule")
    if not text:
        return None
    reason = state.get("_memory_system_rule_reason") or "manual"
    return SystemRuleRequest(text=str(text), reason=str(reason))


def _team_id_from_config(config: object) -> str | None:
    if isinstance(config, dict):
        value = config.get("team_id") or config.get("team")
        return str(value) if value else None
    for attr in ("team_id", "team"):
        value = getattr(config, attr, None)
        if value:
            return str(value)
    return None


def _normalize_path(value: str) -> str:
    try:
        return Path(value).resolve().as_posix()
    except Exception:
        return str(value)


__all__ = ["LaneContext", "SystemRuleRequest", "resolve_team_id", "system_rule_request_from_state"]
