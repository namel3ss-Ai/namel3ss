from __future__ import annotations

from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.packs.layout import pack_path


def resolve_pack_dir(app_root: Path, value: str) -> Path:
    path = Path(value)
    if path.exists():
        return path
    candidate = pack_path(app_root, value)
    if candidate.exists():
        return candidate
    raise Namel3ssError(_missing_pack_message(value, candidate))


def _missing_pack_message(value: str, candidate: Path) -> str:
    return build_guidance_message(
        what="Pack path was not found.",
        why=f"'{value}' was not found (expected {candidate.as_posix()}).",
        fix="Provide a valid pack path or install the pack first.",
        example=f"n3 packs add ./packs/{value}",
    )


__all__ = ["resolve_pack_dir"]
