from __future__ import annotations

import shutil


def detect_container_runtime() -> str | None:
    if shutil.which("docker"):
        return "docker"
    if shutil.which("podman"):
        return "podman"
    return None


__all__ = ["detect_container_runtime"]
