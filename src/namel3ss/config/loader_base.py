from __future__ import annotations

from pathlib import Path

from namel3ss.config.apply_tables import _apply_toml_config
from namel3ss.config.dotenv import apply_dotenv, load_dotenv_for_path
from namel3ss.config.env_loader import apply_env_overrides
from namel3ss.config.model import AppConfig
from namel3ss.config.toml_parser import _parse_toml
from namel3ss.config.types import ConfigSource

CONFIG_FILENAME = "namel3ss.toml"


def load_config(app_path: Path | None = None, root: Path | None = None) -> AppConfig:
    config, _ = resolve_config(app_path=app_path, root=root)
    return config


def resolve_config(
    app_path: Path | None = None,
    root: Path | None = None,
) -> tuple[AppConfig, list[ConfigSource]]:
    config = AppConfig()
    sources: list[ConfigSource] = []
    project_root = _resolve_root(app_path, root)
    if project_root:
        toml_path = project_root / CONFIG_FILENAME
        if toml_path.exists():
            data = _parse_toml(toml_path.read_text(encoding="utf-8"), toml_path)
            _apply_toml_config(config, data)
            sources.append(ConfigSource(kind="toml", path=toml_path.as_posix()))
        env_path = project_root / ".env"
        if env_path.exists():
            apply_dotenv(load_dotenv_for_path(str(env_path)))
            sources.append(ConfigSource(kind="dotenv", path=env_path.as_posix()))
    elif app_path:
        env_path = Path(app_path).resolve().parent / ".env"
        if env_path.exists():
            apply_dotenv(load_dotenv_for_path(str(app_path)))
            sources.append(ConfigSource(kind="dotenv", path=env_path.as_posix()))
    if apply_env_overrides(config):
        sources.append(ConfigSource(kind="env", path=None))
    return config, sources


def _resolve_root(app_path: Path | None, root: Path | None) -> Path | None:
    if root:
        return Path(root).resolve()
    if app_path:
        return Path(app_path).resolve().parent
    return None


__all__ = ["load_config", "resolve_config", "ConfigSource", "CONFIG_FILENAME", "_resolve_root"]
