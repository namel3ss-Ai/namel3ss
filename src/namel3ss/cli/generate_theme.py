from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ui.theme.theme_tokens import normalize_base_theme_name, resolve_base_theme_tokens
from namel3ss.utils.slugify import slugify_text


@dataclass(frozen=True)
class ThemeScaffoldResult:
    target: Path
    files: tuple[str, ...]
    dry_run: bool


def scaffold_theme_config(
    name: str,
    root: Path,
    *,
    base_theme: str = "default",
    dry_run: bool = False,
) -> ThemeScaffoldResult:
    normalized_name = _normalize_name(name)
    normalized_base_theme = normalize_base_theme_name(base_theme)
    target = (root / "themes" / f"{normalized_name}.json").resolve()
    if target.exists():
        raise Namel3ssError(_existing_file_message(target))

    payload = {
        "base_theme": normalized_base_theme,
        "overrides": resolve_base_theme_tokens(normalized_base_theme),
    }
    content = canonical_json_dumps(payload, pretty=True, drop_run_keys=False) + "\n"

    if dry_run:
        return ThemeScaffoldResult(target=target, files=("themes/" + target.name,), dry_run=True)

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return ThemeScaffoldResult(target=target, files=("themes/" + target.name,), dry_run=False)


def _normalize_name(value: str) -> str:
    slug = slugify_text(value)
    if slug:
        return slug
    raise Namel3ssError(
        build_guidance_message(
            what="Theme name is required.",
            why="The generator received an empty theme name.",
            fix="Pass a non-empty theme name.",
            example="n3 create theme enterprise_brand",
        )
    )


def _existing_file_message(path: Path) -> str:
    return build_guidance_message(
        what=f"Theme file already exists: {path.as_posix()}.",
        why="Theme scaffolding does not overwrite existing files.",
        fix="Choose a different theme name or remove the existing file.",
        example="n3 create theme enterprise_brand",
    )


__all__ = ["ThemeScaffoldResult", "scaffold_theme_config"]
