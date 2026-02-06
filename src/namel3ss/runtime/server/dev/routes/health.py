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
    payload = {"ok": True, "status": "ready", "mode": handler._mode()}
    payload["headless"] = bool(getattr(handler.server, "headless", False))  # type: ignore[attr-defined]
    concurrency = getattr(handler.server, "concurrency", None)  # type: ignore[attr-defined]
    if isinstance(concurrency, dict):
        payload["concurrency"] = concurrency
    handler._respond_json(payload)
    return True


__all__ = ["handle_dev_status_get", "handle_health_get"]
