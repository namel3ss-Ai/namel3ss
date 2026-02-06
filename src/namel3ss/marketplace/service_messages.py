from __future__ import annotations

from pathlib import Path

from namel3ss.errors.guidance import build_guidance_message


def registry_root_message() -> str:
    return build_guidance_message(
        what="Marketplace registry path could not be resolved.",
        why="The project root is missing.",
        fix="Run the command from a project with app.ai.",
        example="n3 marketplace search flow",
    )


def missing_files_message(missing: list[str]) -> str:
    return build_guidance_message(
        what="Marketplace manifest references missing files.",
        why=", ".join(missing),
        fix="Update manifest/capability files list or add the missing files.",
        example="files:\n  - app.ai",
    )


def lint_failed_message(path: str, detail: str) -> str:
    return build_guidance_message(
        what="Marketplace item lint failed.",
        why=f"{path}: {detail}",
        fix="Fix lint errors before publishing.",
        example="n3 lint app.ai",
    )


def quality_failed_message(path: str, detail: str) -> str:
    return build_guidance_message(
        what="Marketplace item quality gate failed.",
        why=f"{path}: {detail}",
        fix="Fix quality issues before publishing.",
        example="n3 quality check app.ai",
    )


def non_deterministic_bundle_message() -> str:
    return build_guidance_message(
        what="Marketplace packaging is not deterministic.",
        why="The package bytes changed between two consecutive builds.",
        fix="Remove dynamic fields such as timestamps from package inputs.",
        example="n3 marketplace publish ./item",
    )


def missing_item_message(name: str, version: str) -> str:
    return build_guidance_message(
        what=f'Marketplace item "{name}" was not found.',
        why=f"Version {version} is not in the registry index.",
        fix="Search available items and verify the version.",
        example=f"n3 marketplace search {name}",
    )


def missing_bundle_message(path: Path) -> str:
    return build_guidance_message(
        what="Marketplace bundle is missing.",
        why=f"Expected {path.as_posix()} to exist.",
        fix="Republish the item.",
        example="n3 marketplace publish ./item",
    )


def invalid_bundle_message(path: Path) -> str:
    return build_guidance_message(
        what="Marketplace bundle is invalid.",
        why=f"{path.as_posix()} is missing required files.",
        fix="Republish the item and retry installation.",
        example="n3 marketplace install demo.item",
    )


def invalid_rating_message() -> str:
    return build_guidance_message(
        what="Marketplace rating is invalid.",
        why="Rating must be an integer from 1 to 5.",
        fix="Use a value in that range.",
        example="n3 marketplace rate demo.item 0.1.0 5",
    )


def missing_comment_message() -> str:
    return build_guidance_message(
        what="Marketplace comment is missing.",
        why="Comment text cannot be empty.",
        fix="Provide a non-empty comment string.",
        example='n3 marketplace comment demo.item 0.1.0 --comment "Useful"',
    )


__all__ = [
    "invalid_bundle_message",
    "invalid_rating_message",
    "lint_failed_message",
    "missing_bundle_message",
    "missing_comment_message",
    "missing_files_message",
    "missing_item_message",
    "non_deterministic_bundle_message",
    "quality_failed_message",
    "registry_root_message",
]
