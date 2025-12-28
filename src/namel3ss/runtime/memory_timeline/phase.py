from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional

from namel3ss.runtime.memory.contract import MemoryClock

PHASE_PREFIX = "phase"
DEFAULT_PHASE_REASON = "auto"


@dataclass(frozen=True)
class PhaseInfo:
    phase_id: str
    phase_index: int
    started_at: int
    reason: str
    name: str | None = None


@dataclass(frozen=True)
class PhaseRequest:
    token: str
    name: str | None
    reason: str


def phase_request_from_state(state: Mapping[str, object] | None) -> PhaseRequest | None:
    if not isinstance(state, dict):
        return None
    token = state.get("_memory_phase_token")
    if token is None:
        return None
    token_text = str(token).strip()
    if not token_text:
        return None
    name = state.get("_memory_phase_name")
    reason = state.get("_memory_phase_reason") or "manual"
    return PhaseRequest(token=token_text, name=str(name) if name else None, reason=str(reason))


class PhaseRegistry:
    def __init__(self, *, clock: MemoryClock) -> None:
        self._clock = clock
        self._counters: dict[str, int] = {}
        self._current: dict[str, PhaseInfo] = {}
        self._history: dict[str, list[PhaseInfo]] = {}
        self._last_token: dict[str, str] = {}

    def current(self, store_key: str) -> PhaseInfo | None:
        return self._current.get(store_key)

    def phases(self, store_key: str) -> list[PhaseInfo]:
        return list(self._history.get(store_key, []))

    def ensure_phase(
        self,
        store_key: str,
        *,
        request: PhaseRequest | None = None,
        default_reason: str = DEFAULT_PHASE_REASON,
    ) -> tuple[PhaseInfo, bool]:
        if request and self._should_start_new(store_key, request):
            phase = self._start_phase(store_key, request.reason, request.name, request.token)
            return phase, True
        current = self._current.get(store_key)
        if current is None:
            phase = self._start_phase(store_key, default_reason, None, None)
            return phase, True
        return current, False

    def start_phase(self, store_key: str, *, reason: str, name: str | None = None) -> PhaseInfo:
        return self._start_phase(store_key, reason, name, None)

    def _should_start_new(self, store_key: str, request: PhaseRequest) -> bool:
        last_token = self._last_token.get(store_key)
        if last_token == request.token:
            return False
        return True

    def _start_phase(self, store_key: str, reason: str, name: str | None, token: str | None) -> PhaseInfo:
        index = self._counters.get(store_key, 0) + 1
        self._counters[store_key] = index
        started_at = self._clock.now()
        phase_id = f"{PHASE_PREFIX}-{index}"
        phase = PhaseInfo(
            phase_id=phase_id,
            phase_index=index,
            started_at=started_at,
            reason=reason,
            name=name,
        )
        self._current[store_key] = phase
        self._history.setdefault(store_key, []).append(phase)
        if token is not None:
            self._last_token[store_key] = token
        return phase




__all__ = [
    "DEFAULT_PHASE_REASON",
    "PHASE_PREFIX",
    "PhaseInfo",
    "PhaseRegistry",
    "PhaseRequest",
    "phase_request_from_state",
]
