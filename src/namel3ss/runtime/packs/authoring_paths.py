from __future__ import annotations

from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.packs.layout import local_packs_root, pack_path


def resolve_pack_dir(app_root: Path, value: str) -> Path:
    path = Path(value)
    if path.exists():
        return path
    candidate = pack_path(app_root, value)
    if candidate.exists():
        return candidate
    local_candidate = local_packs_root(app_root) / value
    if local_candidate.exists():
        return local_candidate
    raise Namel3ssError(_missing_pack_message(value, candidate, local_candidate))


def _missing_pack_message(value: str, candidate: Path, local_candidate: Path) -> str:
    return build_guidance_message(
        what="Pack path was not found.",
        why=f"'{value}' was not found (expected {candidate.as_posix()} or {local_candidate.as_posix()}).",
        fix="Provide a valid pack path or install the pack first.",
        example=f"n3 packs add ./packs/capability/{value}",
    )


__all__ = ["resolve_pack_dir"]
