from __future__ import annotations

import os
import shutil
import stat
import sys
import time
from pathlib import Path
from typing import Callable


_WIN_RETRY_ERRORS = {5, 32}


def remove_tree(path: Path, *, retries: int = 3, delay: float = 0.05) -> None:
    """Remove a directory tree, retrying on transient Windows locks."""
    if not path.exists():
        return
    if not _is_windows():
        shutil.rmtree(path)
        return

    def _onerror(func: Callable[[str], None], target: str, exc_info) -> None:
        del exc_info
        try:
            os.chmod(target, stat.S_IWRITE)
        except OSError:
            pass
        func(target)

    attempt = 0
    while True:
        try:
            shutil.rmtree(path, onerror=_onerror)
            return
        except OSError as err:
            winerror = getattr(err, "winerror", None)
            if winerror not in _WIN_RETRY_ERRORS or attempt >= retries:
                raise
            attempt += 1
            time.sleep(delay)


def _is_windows() -> bool:
    return sys.platform.startswith("win")


__all__ = ["remove_tree"]
