from __future__ import annotations

from typing import Any


def handle_dev_status_get(handler: Any, path: str) -> bool:
    if path != "/api/dev/status":
        return False
    payload = handler._state().status_payload()
    status = 200 if payload.get("ok", True) else 400
    handler._respond_json(payload, status=status)
    return True


def handle_health_get(handler: Any, path: str) -> bool:
    if path != "/api/health":
        return False
    handler._respond_json({"ok": True, "status": "ready", "mode": handler._mode()})
    return True


__all__ = ["handle_dev_status_get", "handle_health_get"]
