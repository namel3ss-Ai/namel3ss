from __future__ import annotations

from typing import Any

from namel3ss.runtime.ui.renderer.registry_health_contract import (
    build_renderer_registry_health_payload,
)


RENDERER_REGISTRY_HEALTH_PATH = "/api/renderer-registry/health"


def handle_renderer_registry_health_get(handler: Any, path: str) -> bool:
    normalized_path = str(path or "").rstrip("/") or "/"
    if normalized_path != RENDERER_REGISTRY_HEALTH_PATH:
        return False
    payload = build_renderer_registry_health_payload()
    status = 200 if payload.get("ok") is True else 503
    _respond_json(handler, payload, status=status)
    return True


def _respond_json(handler: Any, payload: dict[str, object], *, status: int) -> None:
    responder = getattr(handler, "_respond_json", None)
    if not callable(responder):
        raise RuntimeError("Renderer registry health route requires handler._respond_json.")
    try:
        responder(payload, status=status, sort_keys=True)
    except TypeError:
        responder(payload, status=status)


__all__ = [
    "RENDERER_REGISTRY_HEALTH_PATH",
    "handle_renderer_registry_health_get",
]
