from __future__ import annotations

import re
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Mapping

from namel3ss.errors.base import Namel3ssError

SPACE_SESSION = "session"
SPACE_USER = "user"
SPACE_PROJECT = "project"
SPACE_SYSTEM = "system"

MEMORY_SPACES = {SPACE_SESSION, SPACE_USER, SPACE_PROJECT, SPACE_SYSTEM}

DEFAULT_OWNER = "anonymous"


@dataclass(frozen=True)
class SpaceContext:
    session_id: str
    user_id: str
    project_id: str
    system_id: str = SPACE_SYSTEM

    def owner_for(self, space: str) -> str:
        if space == SPACE_SESSION:
            return self.session_id
        if space == SPACE_USER:
            return self.user_id
        if space == SPACE_PROJECT:
            return self.project_id
        if space == SPACE_SYSTEM:
            return self.system_id
        raise Namel3ssError(
            "Unknown memory space.",
            details={"space": space},
        )

    def store_key_for(self, space: str, *, lane: str) -> str:
        return store_key(space, self.owner_for(space), lane)


def store_key(space: str, owner: str, lane: str) -> str:
    return f"{space}:{owner}:{lane}"


def resolve_space_context(
    state: Mapping[str, object] | None,
    *,
    identity: Mapping[str, object] | None = None,
    project_root: str | None = None,
    app_path: str | None = None,
) -> SpaceContext:
    session_id = _resolve_session_id(state)
    user_id = _resolve_user_id(state, identity) or session_id
    project_id = _resolve_project_id(project_root, app_path)
    return SpaceContext(
        session_id=normalize_owner(session_id),
        user_id=normalize_owner(user_id),
        project_id=normalize_owner(project_id, default="unknown"),
    )


def ensure_space_meta(meta: Mapping[str, object] | None, *, space: str, owner: str) -> dict:
    payload = dict(meta or {})
    payload.setdefault("space", space)
    payload.setdefault("owner", owner)
    return payload


def validate_space_rules(item: object) -> tuple[str, str]:
    meta = {}
    if hasattr(item, "meta"):
        meta = getattr(item, "meta") or {}
    elif isinstance(item, dict):
        meta = item.get("meta") or {}
    space = meta.get("space")
    owner = meta.get("owner")
    if space not in MEMORY_SPACES:
        raise Namel3ssError(
            "Invalid memory space. Expected one of: session, user, project, system.",
            details={"space": space},
        )
    if not isinstance(owner, str) or not owner:
        raise Namel3ssError(
            "Memory item owner must be a non-empty string.",
            details={"owner": owner},
        )
    return space, owner


def normalize_owner(value: object, *, default: str = DEFAULT_OWNER) -> str:
    if value is None:
        return default
    text = str(value).strip()
    if not text:
        return default
    text = re.sub(r"\s+", "_", text)
    return text.replace(":", "_")


def _resolve_session_id(state: Mapping[str, object] | None) -> str:
    if isinstance(state, dict):
        user = state.get("user")
        if isinstance(user, dict) and "id" in user:
            return str(user["id"])
    return DEFAULT_OWNER


def _resolve_user_id(state: Mapping[str, object] | None, identity: Mapping[str, object] | None) -> str | None:
    if isinstance(identity, dict):
        for key in ("id", "user_id"):
            if key in identity and identity[key]:
                return str(identity[key])
    if isinstance(state, dict):
        user = state.get("user")
        if isinstance(user, dict) and "id" in user:
            return str(user["id"])
    return None


def _resolve_project_id(project_root: str | None, app_path: str | None) -> str:
    seed = None
    if project_root:
        seed = _normalize_path(project_root)
    elif app_path:
        seed = _normalize_path(app_path)
    if not seed:
        return "unknown"
    digest = sha256(seed.encode("utf-8")).hexdigest()
    return digest[:12]


def _normalize_path(value: str) -> str:
    try:
        return Path(value).resolve().as_posix()
    except Exception:
        return str(value)


__all__ = [
    "DEFAULT_OWNER",
    "MEMORY_SPACES",
    "SPACE_PROJECT",
    "SPACE_SESSION",
    "SPACE_SYSTEM",
    "SPACE_USER",
    "SpaceContext",
    "ensure_space_meta",
    "normalize_owner",
    "resolve_space_context",
    "store_key",
    "validate_space_rules",
]
