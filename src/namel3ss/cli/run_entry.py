from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from pathlib import Path

from namel3ss.cli.run_mode import run_run_command
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ui.manifest.display_mode import (
    DISPLAY_MODE_PRODUCTION,
    DISPLAY_MODE_STUDIO,
    is_display_mode,
    normalize_display_mode,
)

_ENV_UI_MODE = "N3_UI_MODE"
_ENV_UI_DIAGNOSTICS = "N3_UI_DIAGNOSTICS"


def dispatch_run_command(args: list[str]) -> int:
    mode = _resolve_requested_mode(args)
    diagnostics_flag_in_args = "--diagnostics" in args
    diagnostics_enabled = _resolve_requested_diagnostics(args)
    if mode == DISPLAY_MODE_STUDIO and diagnostics_flag_in_args:
        print("Warning: --diagnostics is ignored in Studio mode (Studio already includes diagnostics).", file=sys.stderr)
    normalized_args = _strip_mode_tokens(args)
    with _temporary_ui_mode(mode):
        with _temporary_diagnostics_flag(diagnostics_enabled):
            return run_run_command(
                normalized_args,
                ui_mode=mode,
                diagnostics_enabled=diagnostics_enabled,
            )


def _resolve_requested_mode(args: list[str]) -> str:
    mode = DISPLAY_MODE_PRODUCTION

    first = args[0] if args else None
    if first in {DISPLAY_MODE_STUDIO, DISPLAY_MODE_PRODUCTION}:
        mode = normalize_display_mode(first, default=mode)
    elif _looks_like_unknown_mode(first):
        _raise_unknown_mode(str(first))

    has_studio_flag = "--studio" in args
    has_production_flag = "--production" in args
    if has_studio_flag and has_production_flag:
        raise Namel3ssError("Use either --studio or --production, not both.")
    if has_studio_flag:
        mode = DISPLAY_MODE_STUDIO
    elif has_production_flag:
        mode = DISPLAY_MODE_PRODUCTION
    return mode


def _strip_mode_tokens(args: list[str]) -> list[str]:
    cleaned = [arg for arg in args if arg not in {"--studio", "--production", "--diagnostics"}]
    if cleaned and cleaned[0] in {DISPLAY_MODE_STUDIO, DISPLAY_MODE_PRODUCTION}:
        return cleaned[1:]
    return cleaned


def _resolve_requested_diagnostics(args: list[str]) -> bool:
    env_enabled = _env_diagnostics_enabled()
    return "--diagnostics" in args or env_enabled


def _env_diagnostics_enabled() -> bool:
    return os.getenv(_ENV_UI_DIAGNOSTICS, "").strip().lower() in {"1", "true", "yes", "on"}


def _looks_like_unknown_mode(token: str | None) -> bool:
    if token is None:
        return False
    if token.startswith("-"):
        return False
    if is_display_mode(token):
        return False
    if _looks_like_app_path(token):
        return False
    return True


def _looks_like_app_path(token: str) -> bool:
    if token.endswith(".ai"):
        return True
    if "/" in token or "\\" in token:
        return True
    return Path(token).exists()


def _raise_unknown_mode(value: str) -> None:
    raise Namel3ssError(
        build_guidance_message(
            what=f"Unknown run mode '{value}'. Did you mean n3 run or n3 run studio?",
            why="Run mode must be omitted (production) or set to studio.",
            fix="Use n3 run <app.ai> for production, or n3 run studio <app.ai> for Studio.",
            example="n3 run studio app.ai",
        )
    )


@contextmanager
def _temporary_ui_mode(mode: str):
    previous = os.environ.get(_ENV_UI_MODE)
    os.environ[_ENV_UI_MODE] = mode
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop(_ENV_UI_MODE, None)
        else:
            os.environ[_ENV_UI_MODE] = previous


@contextmanager
def _temporary_diagnostics_flag(enabled: bool):
    previous = os.environ.get(_ENV_UI_DIAGNOSTICS)
    os.environ[_ENV_UI_DIAGNOSTICS] = "true" if enabled else "false"
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop(_ENV_UI_DIAGNOSTICS, None)
        else:
            os.environ[_ENV_UI_DIAGNOSTICS] = previous


__all__ = ["dispatch_run_command"]
