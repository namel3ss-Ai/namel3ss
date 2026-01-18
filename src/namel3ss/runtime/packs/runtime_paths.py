from __future__ import annotations

from pathlib import Path


PACK_RUNTIME_DIR = ".namel3ss/packs_runtime"
JOB_QUEUE_FILE = "jobs.jsonl"


def pack_runtime_root(app_root: Path, pack_id: str) -> Path:
    return app_root / PACK_RUNTIME_DIR / pack_id


def pack_job_queue_path(root: Path) -> Path:
    return root / JOB_QUEUE_FILE


__all__ = ["JOB_QUEUE_FILE", "PACK_RUNTIME_DIR", "pack_job_queue_path", "pack_runtime_root"]
