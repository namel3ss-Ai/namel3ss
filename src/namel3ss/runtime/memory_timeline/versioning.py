from __future__ import annotations

from typing import Mapping

from namel3ss.runtime.memory_timeline.phase import PhaseInfo


def apply_phase_meta(meta: Mapping[str, object] | None, phase: PhaseInfo) -> dict:
    payload = dict(meta or {})
    payload["phase_id"] = phase.phase_id
    payload["phase_started_at"] = phase.started_at
    payload["phase_reason"] = phase.reason
    if phase.name:
        payload["phase_name"] = phase.name
    return payload


__all__ = ["apply_phase_meta"]
