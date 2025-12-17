from __future__ import annotations

import os
from pathlib import Path


def load_dotenv_for_path(ai_path: str) -> dict[str, str]:
    path = Path(ai_path).resolve()
    env_path = path.parent / ".env"
    if not env_path.exists():
        return {}
    values: dict[str, str] = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            continue
        key, raw_value = stripped.split("=", 1)
        key = key.strip()
        value = raw_value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values


def apply_dotenv(values: dict[str, str]) -> None:
    for key, value in values.items():
        if key not in os.environ:
            os.environ[key] = value


__all__ = ["load_dotenv_for_path", "apply_dotenv"]
