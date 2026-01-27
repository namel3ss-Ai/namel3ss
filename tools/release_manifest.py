"""
Generate a deterministic release manifest for CI artifacts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional


def run_git(args: list[str], repo_root: Path) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(message or f"git {' '.join(args)} failed")
    return result.stdout.strip()


def read_version(repo_root: Path, version_path: Path) -> str:
    if not version_path.exists():
        raise RuntimeError(f"VERSION file not found at {version_path}.")
    return version_path.read_text(encoding="utf-8").strip()


def normalize_tag(tag: str) -> str:
    if tag.startswith("refs/tags/"):
        return tag.split("refs/tags/", 1)[1]
    return tag


def get_tag(repo_root: Path, override: Optional[str]) -> str:
    if override:
        return normalize_tag(override)
    env_tag = os.environ.get("GITHUB_REF_NAME") or os.environ.get("GITHUB_REF")
    if env_tag:
        return normalize_tag(env_tag)
    return normalize_tag(run_git(["describe", "--tags", "--exact-match"], repo_root))


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def build_manifest(
    repo_root: Path,
    dist_dir: Path,
    version_path: Path,
    docker_tag: str,
    tag_override: Optional[str],
) -> dict:
    version = read_version(repo_root, version_path)
    tag = get_tag(repo_root, tag_override)
    commit = run_git(["rev-parse", "HEAD"], repo_root)

    if not dist_dir.exists():
        raise RuntimeError(f"dist directory not found at {dist_dir}.")

    artifacts: list[dict[str, str]] = []
    for path in sorted(dist_dir.iterdir()):
        if not path.is_file():
            continue
        rel_path = path.relative_to(repo_root)
        artifacts.append({"file": str(rel_path), "sha256": sha256_file(path)})

    if not artifacts:
        raise RuntimeError("No artifacts found in dist; build must run before manifest generation.")

    return {
        "version": version,
        "commit": commit,
        "tag": tag,
        "pypi_artifacts": artifacts,
        "docker_image": docker_tag,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a release manifest JSON file.")
    parser.add_argument("--dist-dir", default="dist", help="Directory containing built artifacts.")
    parser.add_argument("--version-file", default="VERSION", help="Path to VERSION file.")
    parser.add_argument("--tag", help="Release tag (defaults to GITHUB_REF_NAME or git describe).")
    parser.add_argument("--docker-tag", required=True, help="Docker image tag to record.")
    parser.add_argument("--output", default="release_manifest.json", help="Output JSON path.")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    dist_dir = (repo_root / args.dist_dir).resolve()
    version_path = (repo_root / args.version_file).resolve()
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = repo_root / output_path

    try:
        manifest = build_manifest(repo_root, dist_dir, version_path, args.docker_tag, args.tag)
    except RuntimeError as exc:
        print(f"Release manifest failed: {exc}", file=sys.stderr)
        return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Release manifest written to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
