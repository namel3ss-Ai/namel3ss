"""
Release guardrails to ensure tags, VERSION, and CI are aligned before publishing.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class GuardContext:
    repo: str
    tag: str
    version: str
    head_sha: str


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


def read_version(repo_root: Path) -> str:
    version_path = repo_root / "VERSION"
    if not version_path.exists():
        raise RuntimeError("VERSION file not found.")
    return version_path.read_text(encoding="utf-8").strip()


def read_changelog(repo_root: Path) -> str:
    changelog_path = repo_root / "CHANGELOG.md"
    if not changelog_path.exists():
        raise RuntimeError("CHANGELOG.md not found.")
    return changelog_path.read_text(encoding="utf-8")


def extract_notes(changelog: str, version: str) -> str:
    pattern = re.compile(rf"^##\s+v?{re.escape(version)}\b", re.MULTILINE)
    match = pattern.search(changelog)
    if not match:
        raise RuntimeError(f"Release notes for v{version} were not found in CHANGELOG.md.")
    start = match.start()
    following = changelog[match.end() :]
    next_match = re.search(r"^##\s+", following, re.MULTILINE)
    end = match.end() + (next_match.start() if next_match else len(following))
    return changelog[start:end].strip()


def notes_include_runtime_statement(notes: str) -> bool:
    lowered = notes.lower()
    required_phrases = (
        "no grammar/runtime changes",
        "no grammar changes",
        "no runtime changes",
        "no language changes",
        "grammar/runtime: none",
        "grammar: none",
        "runtime: none",
        "language: none",
    )
    return any(phrase in lowered for phrase in required_phrases)


def normalize_tag(tag: str) -> str:
    if tag.startswith("refs/tags/"):
        return tag.split("refs/tags/", 1)[1]
    return tag


def tag_to_version(tag: str) -> str:
    return tag[1:] if tag.startswith("v") else tag


def is_clean(repo_root: Path) -> bool:
    status = run_git(["status", "--porcelain"], repo_root)
    return not status.strip()


def get_tag(repo_root: Path, override: Optional[str]) -> str:
    if override:
        return normalize_tag(override)
    env_tag = os.environ.get("GITHUB_REF_NAME") or os.environ.get("GITHUB_REF")
    if env_tag:
        return normalize_tag(env_tag)
    return normalize_tag(run_git(["describe", "--tags", "--exact-match"], repo_root))


def get_head_sha(repo_root: Path) -> str:
    return run_git(["rev-parse", "HEAD"], repo_root)


def ensure_tag_points_to_head(repo_root: Path, tag: str, head_sha: str) -> None:
    tag_sha = run_git(["rev-parse", tag], repo_root)
    if tag_sha != head_sha:
        raise RuntimeError(
            f"Tag {tag} points to {tag_sha}, but HEAD is {head_sha}. Tag the release commit before publishing."
        )


def parse_repo_from_remote(repo_root: Path) -> str:
    remote = run_git(["config", "--get", "remote.origin.url"], repo_root)
    remote = remote.strip()
    if remote.startswith("git@") and ":" in remote:
        _, path = remote.split(":", 1)
        return path.removesuffix(".git")
    if remote.startswith("https://") or remote.startswith("http://"):
        path = remote.split("//", 1)[1]
        parts = path.split("/", 1)
        if len(parts) == 2:
            return parts[1].removesuffix(".git")
    raise RuntimeError("Unable to determine GitHub repo from remote.origin.url.")


def require_ci_success(repo: str, sha: str, token: str, workflow: str) -> None:
    url = (
        f"https://api.github.com/repos/{repo}/actions/workflows/{workflow}/runs"
        f"?head_sha={sha}&status=success"
    )
    request = Request(url)
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("Authorization", f"Bearer {token}")
    try:
        with urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError) as exc:
        raise RuntimeError(f"Failed to query GitHub Actions API: {exc}") from exc

    if payload.get("total_count", 0) < 1:
        raise RuntimeError(
            f"CI workflow {workflow} has no successful runs for commit {sha}. "
            "Wait for CI to finish or re-run it before publishing."
        )


def build_context(repo_root: Path, tag_override: Optional[str]) -> GuardContext:
    version = read_version(repo_root)
    tag = get_tag(repo_root, tag_override)
    head_sha = get_head_sha(repo_root)
    repo = os.environ.get("GITHUB_REPOSITORY") or parse_repo_from_remote(repo_root)
    return GuardContext(repo=repo, tag=tag, version=version, head_sha=head_sha)


def run_checks(ctx: GuardContext, repo_root: Path, require_ci: bool, workflow: str) -> None:
    if not is_clean(repo_root):
        raise RuntimeError("Working tree is not clean. Commit or stash changes before publishing.")

    tag_version = tag_to_version(ctx.tag)
    if tag_version != ctx.version:
        raise RuntimeError(
            f"VERSION is {ctx.version}, but tag is {ctx.tag}. "
            "Update VERSION or retag so they match."
        )

    ensure_tag_points_to_head(repo_root, ctx.tag, ctx.head_sha)

    if require_ci:
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if not token:
            raise RuntimeError("GITHUB_TOKEN is required to verify CI status.")
        require_ci_success(ctx.repo, ctx.head_sha, token, workflow)

    changelog = read_changelog(repo_root)
    notes = extract_notes(changelog, ctx.version)
    if not notes_include_runtime_statement(notes):
        raise RuntimeError(
            f"Release notes for v{ctx.version} must state grammar/runtime change status. "
            "Add a line like 'No grammar/runtime changes.' to CHANGELOG.md."
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate release preconditions.")
    parser.add_argument("--tag", help="Release tag (defaults to GITHUB_REF_NAME or git describe).")
    parser.add_argument(
        "--require-ci",
        action="store_true",
        help="Require a successful CI run for this commit via the GitHub API.",
    )
    parser.add_argument("--workflow", default="ci.yml", help="Workflow file name to verify.")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    try:
        ctx = build_context(repo_root, args.tag)
        run_checks(ctx, repo_root, args.require_ci, args.workflow)
    except RuntimeError as exc:
        print(f"Release guard failed: {exc}", file=sys.stderr)
        return 1

    print("Release guard ok.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
