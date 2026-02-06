from __future__ import annotations

from namel3ss.version import get_version


def build_health_payload(server) -> dict[str, object]:
    return {
        "ok": True,
        "status": "ready",
        "headless": bool(getattr(server, "headless", False)),
        "target": getattr(server, "target", "service"),
        "process_model": getattr(server, "process_model", "service"),
        "concurrency": getattr(server, "concurrency", None),
        "build_id": getattr(server, "build_id", None),
        "app_path": getattr(server, "app_path", None),
        "summary": getattr(server, "program_summary", {}),
    }


def build_version_payload(server) -> dict[str, object]:
    return {
        "ok": True,
        "version": get_version(),
        "target": getattr(server, "target", "service"),
        "build_id": getattr(server, "build_id", None),
    }


__all__ = ["build_health_payload", "build_version_payload"]

