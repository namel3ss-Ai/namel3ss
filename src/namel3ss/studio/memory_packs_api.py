from __future__ import annotations

from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.studio.session import SessionState


def get_memory_packs_payload(app_path: str, session: SessionState) -> dict:
    project_root = str(Path(app_path).parent)
    try:
        session.memory_manager.ensure_restored(project_root=project_root, app_path=app_path)
        return session.memory_manager.pack_summary(project_root=project_root, app_path=app_path)
    except Namel3ssError as err:
        return {"ok": False, "error": str(err)}


__all__ = ["get_memory_packs_payload"]
