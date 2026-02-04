from __future__ import annotations

from typing import Any

from namel3ss.runtime.server.dev.errors import error_from_message


def handle_answer_explain_get(handler: Any, path: str) -> bool:
    if path != "/api/answer/explain":
        return False
    state = handler._state()
    state._refresh_if_needed()
    session = getattr(state, "session", None)
    explain = getattr(session, "last_answer_explain", None) if session is not None else None
    if not isinstance(explain, dict):
        payload = error_from_message(
            "Answer explain data is unavailable.",
            kind="engine",
            mode=handler._mode(),
            debug=state.debug,
        )
        handler._respond_json(payload, status=404)
        return True
    handler._respond_json({"ok": True, "explain": explain}, status=200)
    return True


__all__ = ["handle_answer_explain_get"]
