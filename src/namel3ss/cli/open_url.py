from __future__ import annotations

import os
import sys
import webbrowser
from typing import Mapping, TextIO


_TRUTHY = {"1", "true", "yes"}


def should_open_url(
    no_open: bool,
    *,
    env: Mapping[str, str] | None = None,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> bool:
    if no_open:
        return False
    env = env or os.environ
    if _env_truthy(env, "N3_NO_OPEN"):
        return False
    if _env_truthy(env, "CI"):
        return False
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr
    if not _has_tty(stdin, stdout, stderr):
        return False
    return True


def open_url(url: str) -> bool:
    try:
        return bool(webbrowser.open(url, new=2))
    except Exception:
        return False


def _env_truthy(env: Mapping[str, str], key: str) -> bool:
    value = env.get(key, "")
    return value.strip().lower() in _TRUTHY


def _has_tty(*streams: TextIO) -> bool:
    for stream in streams:
        try:
            if stream.isatty():
                return True
        except Exception:
            continue
    return False


__all__ = ["open_url", "should_open_url"]
