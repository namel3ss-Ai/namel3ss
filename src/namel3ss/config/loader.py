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
    openai_cfg = data.get("openai", {})
    if isinstance(openai_cfg, dict):
        if "api_key" in openai_cfg:
            config.openai.api_key = str(openai_cfg["api_key"])
        if "base_url" in openai_cfg:
            config.openai.base_url = str(openai_cfg["base_url"])
    anthropic_cfg = data.get("anthropic", {})
    if isinstance(anthropic_cfg, dict) and "api_key" in anthropic_cfg:
        config.anthropic.api_key = str(anthropic_cfg["api_key"])
    gemini_cfg = data.get("gemini", {})
    if isinstance(gemini_cfg, dict) and "api_key" in gemini_cfg:
        config.gemini.api_key = str(gemini_cfg["api_key"])
    mistral_cfg = data.get("mistral", {})
    if isinstance(mistral_cfg, dict) and "api_key" in mistral_cfg:
        config.mistral.api_key = str(mistral_cfg["api_key"])


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
    api_key = os.getenv("NAMEL3SS_OPENAI_API_KEY")
    if api_key:
        config.openai.api_key = api_key
    base_url = os.getenv("NAMEL3SS_OPENAI_BASE_URL")
    if base_url:
        config.openai.base_url = base_url
    anthropic_key = os.getenv("NAMEL3SS_ANTHROPIC_API_KEY")
    if anthropic_key:
        config.anthropic.api_key = anthropic_key
    gemini_key = os.getenv("NAMEL3SS_GEMINI_API_KEY")
    if gemini_key:
        config.gemini.api_key = gemini_key
    mistral_key = os.getenv("NAMEL3SS_MISTRAL_API_KEY")
    if mistral_key:
        config.mistral.api_key = mistral_key


__all__ = ["load_config", "CONFIG_PATH"]
