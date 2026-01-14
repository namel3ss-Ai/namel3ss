from __future__ import annotations

import shutil
from pathlib import Path, PurePosixPath


ARTIFACT_ROOT_NAME = ".namel3ss"


class ArtifactContractError(Exception):
    """Raised when an artifact operation is unsafe or invalid."""


def _normalize_root(root: Path) -> Path:
    try:
        return root.expanduser().resolve()
    except Exception:
        # Fallback to a best-effort path when resolve fails (e.g., missing parents).
        return root


def _validate_root(root: Path) -> None:
    if root.name != ARTIFACT_ROOT_NAME:
        raise ArtifactContractError(f"Artifact root must be {ARTIFACT_ROOT_NAME}.")


def _is_within_root(root: Path, target: Path) -> bool:
    try:
        return target.resolve().is_relative_to(root.resolve())
    except AttributeError:
        # Python <3.9 fallback
        try:
            target_resolved = target.resolve()
            root_resolved = root.resolve()
            return str(target_resolved).startswith(str(root_resolved))
        except Exception:
            return False
    except Exception:
        return False


class ArtifactContract:
    def __init__(self, root: str | Path):
        if root is None:
            raise ArtifactContractError("Artifact root is missing.")
        normalized = _normalize_root(Path(root))
        _validate_root(normalized)
        self.root = normalized

    def normalize_relative(self, rel_path: str | Path) -> str:
        if rel_path is None:
            raise ArtifactContractError("Artifact path is required.")
        try:
            candidate = Path(rel_path)
        except Exception as err:
            raise ArtifactContractError("Invalid artifact path.") from err
        if candidate.is_absolute():
            raise ArtifactContractError("Artifact paths must be relative.")

        parts: list[str] = []
        for part in candidate.parts:
            if part in ("", "."):
                continue
            if part == "..":
                raise ArtifactContractError("Artifact paths cannot escape the artifact root.")
            parts.append(part)
        if not parts:
            raise ArtifactContractError("Artifact path is required.")
        return PurePosixPath(*parts).as_posix()

    def resolve(self, rel_path: str | Path) -> Path:
        normalized = self.normalize_relative(rel_path)
        target = self.root / normalized
        if not _is_within_root(self.root, target):
            raise ArtifactContractError("Artifact path is outside .namel3ss.")
        return target

    def ensure_root_dir(self) -> Path:
        if self.root.exists() and not self.root.is_dir():
            raise ArtifactContractError("Artifact root exists and is not a directory.")
        self.root.mkdir(parents=True, exist_ok=True)
        return self.root

    def ensure_dir(self, rel_path: str | Path) -> Path:
        target = self.resolve(rel_path)
        target.mkdir(parents=True, exist_ok=True)
        return target

    def prepare_file(self, rel_path: str | Path) -> Path:
        target = self.resolve(rel_path)
        self.ensure_root_dir()
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    def delete_paths(self, rel_paths: list[str] | tuple[str, ...]) -> None:
        if not rel_paths:
            return
        for rel in rel_paths:
            target = self.resolve(rel)
            try:
                if target.is_symlink() or target.is_file():
                    target.unlink(missing_ok=True)
                elif target.is_dir():
                    shutil.rmtree(target)
            except FileNotFoundError:
                continue
            except Exception as err:
                raise ArtifactContractError(f"Failed to delete artifact path: {rel}") from err

    def delete_root(self) -> None:
        if not self.root.exists():
            return
        _validate_root(self.root)
        try:
            shutil.rmtree(self.root)
        except Exception as err:
            raise ArtifactContractError(f"Failed to delete artifact root at {self.root}") from err


__all__ = ["ARTIFACT_ROOT_NAME", "ArtifactContract", "ArtifactContractError"]
