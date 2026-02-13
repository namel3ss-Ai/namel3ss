from __future__ import annotations

import os
from pathlib import Path


def is_process_running(pid: int) -> bool:
    process_id = int(pid)
    if process_id <= 0:
        return False
    try:
        os.kill(process_id, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def recover_stale_port_lock(lock_path: Path, *, owner_pid: int) -> bool:
    if owner_pid > 0 and is_process_running(owner_pid):
        return False
    try:
        lock_path.unlink()
    except FileNotFoundError:
        return True
    except OSError:
        return False
    return True


__all__ = [
    "is_process_running",
    "recover_stale_port_lock",
]
