from __future__ import annotations

import difflib
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterable

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ui.settings import closest_value
from namel3ss.validation import ValidationWarning, add_warning


_ALLOWED_MEDIA_EXTENSIONS: tuple[str, ...] = (".png", ".jpg", ".jpeg", ".svg", ".webp")
_MEDIA_ROLE_VALUES: tuple[str, ...] = ("iconic", "illustration", "hero")


class MediaValidationMode(str, Enum):
    CHECK = "check"
    BUILD = "build"

    @classmethod
    def from_value(cls, value: object | None) -> "MediaValidationMode":
        if isinstance(value, cls):
            return value
        if value is None:
            return cls.CHECK
        if isinstance(value, str):
            lowered = value.lower()
            if lowered in {"check", "build"}:
                return cls(lowered)
        raise ValueError(f"Unknown media validation mode: {value}")


@dataclass(frozen=True)
class MediaIntent:
    media_name: str
    role: str | None
    missing: bool
    fix_hint: str | None = None

    def as_dict(self) -> dict:
        payload: dict[str, object] = {"media_name": self.media_name}
        if self.role is not None:
            payload["role"] = self.role
        payload["missing"] = bool(self.missing)
        if self.missing and self.fix_hint:
            payload["fix_hint"] = self.fix_hint
        return payload


def allowed_media_extensions() -> tuple[str, ...]:
    return _ALLOWED_MEDIA_EXTENSIONS


def normalize_media_name(value: str | None) -> str:
    if value is None:
        return ""
    return value.strip().lower().replace(" ", "_").replace("-", "_")


def media_root_for_program(program) -> Path | None:
    if program is None:
        return None
    app_path = getattr(program, "app_path", None)
    if app_path:
        return Path(app_path).resolve().parent / "media"
    project_root = getattr(program, "project_root", None)
    if project_root:
        return Path(project_root).resolve() / "media"
    return None


def media_names(*, root: Path | None = None, program=None) -> tuple[str, ...]:
    registry = _media_registry(_resolve_media_root(root=root, program=program))
    return tuple(sorted(registry.keys()))


def media_registry(*, root: Path | None = None, program=None) -> dict[str, Path]:
    return _media_registry(_resolve_media_root(root=root, program=program))


def resolve_media_file(name: str, *, root: Path | None = None, program=None) -> Path | None:
    registry = _media_registry(_resolve_media_root(root=root, program=program))
    normalized = _validate_media_reference_name(name, line=None, column=None)
    return registry.get(normalized)


def closest_media_name(
    name: str,
    choices: Iterable[str] | None = None,
    *,
    root: Path | None = None,
    program=None,
) -> str | None:
    normalized = normalize_media_name(name)
    available = list(choices) if choices is not None else list(media_names(root=root, program=program))
    suggestions = _suggest_media_names(normalized, available, limit=1)
    return suggestions[0] if suggestions else None


def validate_media_role(value: str | None, *, line: int | None, column: int | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        raise Namel3ssError("Image role cannot be empty.", line=line, column=column)
    if normalized in _MEDIA_ROLE_VALUES:
        return normalized
    suggestion = closest_value(normalized, _MEDIA_ROLE_VALUES)
    fix = f'Did you mean "{suggestion}"?' if suggestion else f"Use one of: {', '.join(_MEDIA_ROLE_VALUES)}."
    raise Namel3ssError(
        build_guidance_message(
            what=f"Unknown image role '{normalized}'.",
            why=f"Allowed roles: {', '.join(_MEDIA_ROLE_VALUES)}.",
            fix=fix,
            example='image is "welcome":\n  role is "hero"',
        ),
        line=line,
        column=column,
    )


def validate_media_reference(
    value: str,
    *,
    root: Path | None = None,
    program=None,
    registry: dict[str, Path] | None = None,
    role: str | None = None,
    mode: MediaValidationMode | str | None = None,
    warnings: list[ValidationWarning] | None = None,
    line: int | None = None,
    column: int | None = None,
) -> MediaIntent:
    normalized = _validate_media_reference_name(value, line=line, column=column)
    media_mode = MediaValidationMode.from_value(mode)
    registry = registry if registry is not None else _media_registry(_resolve_media_root(root=root, program=program))
    if normalized not in registry:
        fix_hint = _missing_media_fix_hint(normalized)
        suggestions = _suggest_media_names(normalized, registry.keys())
        suggestion_hint = _format_suggestions(suggestions)
        fix = f"{fix_hint} {suggestion_hint}".strip()
        message = f"Media '{value}' is missing from media/."
        if suggestion_hint:
            message = f"{message} {suggestion_hint}"
        if media_mode == MediaValidationMode.BUILD:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Missing media '{value}'.",
                    why="Images must match a file in the media/ folder.",
                    fix=fix,
                    example='image is "welcome"',
                ),
                line=line,
                column=column,
                details={"error_id": "media.missing", "keyword": normalized},
            )
        add_warning(
            warnings,
            code="media.missing",
            message=message,
            fix=fix,
            line=line,
            column=column,
        )
        return MediaIntent(media_name=normalized, role=role, missing=True, fix_hint=fix_hint)
    return MediaIntent(media_name=normalized, role=role, missing=False, fix_hint=None)


def _resolve_media_root(*, root: Path | None, program) -> Path | None:
    if root is not None:
        return Path(root)
    return media_root_for_program(program)


def _media_registry(root: Path | None) -> dict[str, Path]:
    if root is None:
        return {}
    if not root.exists():
        return {}
    if not root.is_dir():
        raise Namel3ssError(
            build_guidance_message(
                what="media/ exists but is not a folder.",
                why="Images must live in a media/ directory next to app.ai.",
                fix="Replace media/ with a folder and put images inside it.",
                example="media/welcome.png",
            )
        )
    entries = [path for path in root.iterdir() if path.is_file() and not path.name.startswith(".")]
    entries = sorted(entries, key=lambda p: p.as_posix())
    invalid = [path.name for path in entries if path.suffix.lower() not in _ALLOWED_MEDIA_EXTENSIONS]
    if invalid:
        invalid_sorted = ", ".join(sorted(invalid))
        raise Namel3ssError(
            build_guidance_message(
                what=f"Unsupported media file(s): {invalid_sorted}.",
                why=f"Allowed formats: {', '.join(_ALLOWED_MEDIA_EXTENSIONS)}.",
                fix="Convert the file or remove it from media/.",
                example="media/welcome.png",
            )
        )
    mapping: dict[str, Path] = {}
    collisions: dict[str, list[str]] = {}
    invalid_names: list[str] = []
    for path in entries:
        stem = path.stem
        normalized = normalize_media_name(stem)
        if not normalized:
            invalid_names.append(path.name)
            continue
        if normalized in mapping:
            collisions.setdefault(normalized, [mapping[normalized].name]).append(path.name)
            continue
        mapping[normalized] = path
    if invalid_names:
        invalid_sorted = ", ".join(sorted(invalid_names))
        raise Namel3ssError(
            build_guidance_message(
                what=f"Media file name(s) are invalid: {invalid_sorted}.",
                why="Media files must use a non-empty base name.",
                fix="Rename the file to use a non-empty base name.",
                example="media/welcome.png",
            ),
            details={"error_id": "media.invalid"},
        )
    if collisions:
        name = sorted(collisions.keys())[0]
        files = sorted(collisions[name])
        joined = ", ".join(files)
        raise Namel3ssError(
            build_guidance_message(
                what=f"Media name '{name}' maps to multiple files: {joined}.",
                why="Media names must be unique by base name.",
                fix="Rename one file so each base name is unique.",
                example="media/welcome.png",
            ),
            details={"error_id": "media.collision", "keyword": name},
        )
    return mapping


def _validate_media_reference_name(value: str, *, line: int | None, column: int | None) -> str:
    raw = value.strip() if isinstance(value, str) else ""
    if not raw:
        raise Namel3ssError("Image name cannot be empty.", line=line, column=column, details={"error_id": "media.invalid"})
    if "/" in raw or "\\" in raw:
        raise Namel3ssError(
            build_guidance_message(
                what=f"Image reference '{value}' uses a path.",
                why="Images must be referenced by base name only (no paths).",
                fix="Remove the path and keep only the base name.",
                example='image is "welcome"',
            ),
            line=line,
            column=column,
            details={"error_id": "media.invalid", "keyword": raw},
        )
    lowered = raw.lower()
    if any(lowered.endswith(ext) for ext in _ALLOWED_MEDIA_EXTENSIONS):
        raise Namel3ssError(
            build_guidance_message(
                what=f"Image reference '{value}' includes an extension.",
                why="Images must be referenced by base name only (no extensions).",
                fix="Drop the extension and keep only the base name.",
                example='image is "welcome"',
            ),
            line=line,
            column=column,
            details={"error_id": "media.invalid", "keyword": raw},
        )
    normalized = normalize_media_name(raw)
    if not normalized:
        raise Namel3ssError("Image name cannot be empty.", line=line, column=column, details={"error_id": "media.invalid"})
    return normalized


def _suggest_media_names(name: str, choices: Iterable[str], *, limit: int = 3) -> list[str]:
    pool = sorted({normalize_media_name(choice) for choice in choices if choice})
    return difflib.get_close_matches(name, pool, n=limit, cutoff=0.6)


def _format_suggestions(suggestions: list[str]) -> str:
    if not suggestions:
        return ""
    joined = ", ".join(f'"{name}"' for name in suggestions)
    if len(suggestions) == 1:
        return f"Did you mean {joined}?"
    return f"Did you mean one of {joined}?"


def _missing_media_fix_hint(name: str) -> str:
    return f"Put {name}.png (or .jpg/.jpeg/.svg/.webp) in media/."


__all__ = [
    "MediaIntent",
    "MediaValidationMode",
    "allowed_media_extensions",
    "closest_media_name",
    "media_names",
    "media_registry",
    "media_root_for_program",
    "normalize_media_name",
    "resolve_media_file",
    "validate_media_reference",
    "validate_media_role",
]
