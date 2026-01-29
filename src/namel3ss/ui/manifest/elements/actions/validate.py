from __future__ import annotations

from pathlib import Path

from namel3ss.media import MediaValidationMode, validate_media_reference


def validate_image_reference(
    src: str,
    *,
    registry: dict[str, Path],
    role: str | None,
    mode: MediaValidationMode,
    warnings: list | None,
    line: int | None,
    column: int | None,
):
    return validate_media_reference(
        src,
        registry=registry,
        role=role,
        mode=mode,
        warnings=warnings,
        line=line,
        column=column,
    )


__all__ = ["validate_image_reference"]
