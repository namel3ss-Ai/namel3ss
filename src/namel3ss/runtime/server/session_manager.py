from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import threading
import time

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.memory.api import MemoryManager
from namel3ss.runtime.server.session_scoped_store import SessionScopedStore

DEFAULT_ALLOWED_ROLES = ("guest", "user", "admin")
DEFAULT_IDLE_TIMEOUT_SECONDS = 30 * 60


@dataclass
class ServiceSession:
    session_id: str
    role: str
    store: SessionScopedStore
    memory_manager: MemoryManager
    state: dict = field(default_factory=dict)
    runtime_theme: str | None = None
    created_at_epoch: float = field(default_factory=time.time)
    last_activity_epoch: float = field(default_factory=time.time)
    trace_events: list[dict] = field(default_factory=list)

    def touch(self) -> None:
        self.last_activity_epoch = time.time()


class ServiceSessionManager:
    """Deterministic runtime session lifecycle for service mode."""

    def __init__(
        self,
        *,
        base_store,
        project_root: str | None,
        app_path: str | None,
        allow_multi_user: bool,
        remote_studio_enabled: bool,
        idle_timeout_seconds: int | None = None,
        allowed_roles: tuple[str, ...] = DEFAULT_ALLOWED_ROLES,
    ) -> None:
        self._base_store = base_store
        self._project_root = project_root
        self._app_path = app_path
        self._allow_multi_user = bool(allow_multi_user)
        self._remote_studio_enabled = bool(remote_studio_enabled)
        self._idle_timeout_seconds = _normalize_idle_timeout(idle_timeout_seconds)
        self._allowed_roles = tuple(dict.fromkeys(role.strip().lower() for role in allowed_roles if role)) or DEFAULT_ALLOWED_ROLES
        self._sessions: dict[str, ServiceSession] = {}
        self._counter = 0
        self._lock = threading.RLock()

    @property
    def remote_studio_enabled(self) -> bool:
        return self._remote_studio_enabled

    def ensure_session(
        self,
        *,
        session_id: str | None,
        requested_role: str | None,
        create_if_missing: bool,
    ) -> ServiceSession:
        with self._lock:
            self.cleanup_idle_sessions()
            normalized_role = self._normalize_role(requested_role)
            if session_id:
                existing = self._sessions.get(session_id)
                if existing is None:
                    if not create_if_missing:
                        raise Namel3ssError(_missing_session_message(session_id))
                    return self._create_session(normalized_role)
                if normalized_role and normalized_role != existing.role:
                    raise Namel3ssError(_role_mismatch_message(existing.role, normalized_role))
                existing.touch()
                return existing
            if not create_if_missing:
                raise Namel3ssError(_missing_session_id_message())
            return self._create_session(normalized_role)

    def list_sessions(self) -> list[dict[str, object]]:
        with self._lock:
            self.cleanup_idle_sessions()
            items: list[dict[str, object]] = []
            for session_id in sorted(self._sessions.keys()):
                session = self._sessions[session_id]
                items.append(
                    {
                        "session_id": session.session_id,
                        "role": session.role,
                        "active_since": _iso_timestamp(session.created_at_epoch),
                        "last_activity": _iso_timestamp(session.last_activity_epoch),
                        "state_size": _state_size(session.state),
                    }
                )
            return items

    def kill_session(self, session_id: str) -> bool:
        with self._lock:
            removed = self._sessions.pop(session_id, None)
            return removed is not None

    def record_trace(self, session_id: str, event: dict[str, object]) -> None:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return
            sequence = len(session.trace_events) + 1
            payload = {
                "sequence": sequence,
                "time": _iso_timestamp(time.time()),
                **dict(event or {}),
            }
            session.trace_events.append(payload)
            session.touch()

    def studio_state(self, session_id: str) -> dict:
        with self._lock:
            self.cleanup_idle_sessions()
            session = self._sessions.get(session_id)
            if session is None:
                raise Namel3ssError(_missing_session_message(session_id))
            session.touch()
            return {
                "session_id": session.session_id,
                "role": session.role,
                "state": dict(session.state or {}),
                "runtime_theme": session.runtime_theme,
                "active_since": _iso_timestamp(session.created_at_epoch),
                "last_activity": _iso_timestamp(session.last_activity_epoch),
            }

    def studio_traces(self, session_id: str) -> list[dict]:
        with self._lock:
            self.cleanup_idle_sessions()
            session = self._sessions.get(session_id)
            if session is None:
                raise Namel3ssError(_missing_session_message(session_id))
            session.touch()
            return [dict(item) for item in session.trace_events]

    def cleanup_idle_sessions(self) -> None:
        if self._idle_timeout_seconds <= 0:
            return
        cutoff = time.time() - float(self._idle_timeout_seconds)
        stale_ids = [sid for sid, session in self._sessions.items() if session.last_activity_epoch < cutoff]
        for session_id in stale_ids:
            self._sessions.pop(session_id, None)

    def _create_session(self, requested_role: str | None) -> ServiceSession:
        if not self._allow_multi_user and self._sessions:
            existing = next(iter(sorted(self._sessions.keys())))
            raise Namel3ssError(_multi_user_disabled_message(existing))
        role = requested_role or "guest"
        if role not in self._allowed_roles:
            raise Namel3ssError(_invalid_role_message(role, self._allowed_roles))
        self._counter += 1
        session_id = f"s{self._counter:06d}"
        scoped_store = SessionScopedStore(self._base_store, session_id)
        state = scoped_store.load_state()
        session = ServiceSession(
            session_id=session_id,
            role=role,
            state=state,
            store=scoped_store,
            memory_manager=MemoryManager(project_root=self._project_root, app_path=self._app_path),
        )
        self._sessions[session_id] = session
        return session

    def _normalize_role(self, role: str | None) -> str | None:
        if role is None:
            return None
        value = str(role).strip().lower()
        if not value:
            return None
        return value



def _normalize_idle_timeout(value: int | None) -> int:
    if value is None:
        return DEFAULT_IDLE_TIMEOUT_SECONDS
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return DEFAULT_IDLE_TIMEOUT_SECONDS
    return max(0, parsed)



def _iso_timestamp(epoch_seconds: float) -> str:
    return datetime.fromtimestamp(float(epoch_seconds), tz=timezone.utc).isoformat()



def _state_size(state: dict) -> int:
    try:
        return len(json.dumps(state or {}, sort_keys=True))
    except Exception:
        return 0



def _missing_session_message(session_id: str) -> str:
    return build_guidance_message(
        what=f"Session '{session_id}' was not found.",
        why="The session may have expired, been terminated, or never existed.",
        fix="Create a new session or list active sessions.",
        example="n3 session list",
    )



def _missing_session_id_message() -> str:
    return build_guidance_message(
        what="Session id is required.",
        why="This endpoint needs a session identifier to route state deterministically.",
        fix="Provide X-N3-Session-Id or create a new session first.",
        example="POST /api/service/sessions",
    )



def _invalid_role_message(role: str, allowed: tuple[str, ...]) -> str:
    allowed_text = ", ".join(allowed)
    return build_guidance_message(
        what=f"Role '{role}' is not allowed.",
        why=f"Allowed roles are: {allowed_text}.",
        fix="Use one of the allowed role values.",
        example="X-N3-Role: user",
    )



def _role_mismatch_message(expected: str, got: str) -> str:
    return build_guidance_message(
        what="Session role mismatch.",
        why=f"Session role is '{expected}' but request provided '{got}'.",
        fix="Use the existing session role or create a new session with the intended role.",
        example="POST /api/service/sessions",
    )



def _multi_user_disabled_message(existing_session_id: str) -> str:
    return build_guidance_message(
        what="Multiple sessions are disabled for this service.",
        why=f"Capability 'multi_user' is not enabled; active session is {existing_session_id}.",
        fix="Enable multi_user capability or reuse the existing session id.",
        example='capabilities:\n  service\n  multi_user',
    )


__all__ = [
    "DEFAULT_ALLOWED_ROLES",
    "DEFAULT_IDLE_TIMEOUT_SECONDS",
    "ServiceSession",
    "ServiceSessionManager",
]
