from __future__ import annotations

import json
import os
from pathlib import Path

from namel3ss.config.model import AppConfig
from namel3ss.errors.base import Namel3ssError


CONFIG_PATH = Path.home() / ".namel3ss" / "config.json"


def load_config(config_path: Path | None = None) -> AppConfig:
    config = AppConfig()
    path = config_path or CONFIG_PATH
    if path.exists():
        _apply_file_config(config, path)
    _apply_env_overrides(config)
    return config


def _apply_file_config(config: AppConfig, path: Path) -> None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        raise Namel3ssError(f"Invalid config file at {path}: {err}") from err
    if not isinstance(data, dict):
        raise Namel3ssError(f"Config file must contain an object at {path}")
    ollama_cfg = data.get("ollama", {})
    if isinstance(ollama_cfg, dict):
        if "host" in ollama_cfg:
            config.ollama.host = str(ollama_cfg["host"])
        if "timeout_seconds" in ollama_cfg:
            try:
                config.ollama.timeout_seconds = int(ollama_cfg["timeout_seconds"])
            except (TypeError, ValueError) as err:
                raise Namel3ssError("ollama.timeout_seconds must be an integer") from err


def _apply_env_overrides(config: AppConfig) -> None:
    host = os.getenv("NAMEL3SS_OLLAMA_HOST")
    if host:
        config.ollama.host = host
    timeout = os.getenv("NAMEL3SS_OLLAMA_TIMEOUT_SECONDS")
    if timeout:
        try:
            config.ollama.timeout_seconds = int(timeout)
        except ValueError as err:
            raise Namel3ssError("NAMEL3SS_OLLAMA_TIMEOUT_SECONDS must be an integer") from err


__all__ = ["load_config", "CONFIG_PATH"]
