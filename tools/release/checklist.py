from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from namel3ss.determinism import canonical_json_dumps


_SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:[abrc]\d+)?$")


@dataclass(frozen=True)
class ChecklistResult:
    ok: bool
    checks: tuple[tuple[str, str], ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "checks": [{"name": name, "status": status} for name, status in self.checks],
        }


def run_checklist(repo_root: Path) -> ChecklistResult:
    checks: list[tuple[str, str]] = []
    checks.append(_check_required_files(repo_root))
    checks.append(_check_version(repo_root))
    checks.append(_check_changelog_entry(repo_root))
    checks.append(_check_release_workflow(repo_root))
    ordered = tuple(sorted(checks, key=lambda item: item[0]))
    ok = all(status == "pass" for _, status in ordered)
    return ChecklistResult(ok=ok, checks=ordered)


def _check_required_files(repo_root: Path) -> tuple[str, str]:
    required = (
        "GOVERNANCE.md",
        "CONTRIBUTING.md",
        "CODE_OF_CONDUCT.md",
        "SECURITY.md",
        "docs/compatibility_policy.md",
        "docs/deprecation_policy.md",
        "docs/ga_release.md",
        "docs/architecture_overview.md",
        "tools/release/checklist.py",
        "tools/release/changelog.py",
        ".github/workflows/release.yml",
    )
    missing = [path for path in required if not (repo_root / path).exists()]
    return ("required_files", "pass" if not missing else "fail")


def _check_version(repo_root: Path) -> tuple[str, str]:
    version_path = repo_root / "VERSION"
    if not version_path.exists():
        return ("version_format", "fail")
    version = version_path.read_text(encoding="utf-8").strip()
    return ("version_format", "pass" if _SEMVER.fullmatch(version) else "fail")


def _check_changelog_entry(repo_root: Path) -> tuple[str, str]:
    version_path = repo_root / "VERSION"
    changelog_path = repo_root / "CHANGELOG.md"
    if not version_path.exists() or not changelog_path.exists():
        return ("changelog_entry", "fail")
    version = version_path.read_text(encoding="utf-8").strip()
    changelog = changelog_path.read_text(encoding="utf-8")
    has_entry = re.search(rf"^##\s+v?{re.escape(version)}\b", changelog, flags=re.MULTILINE) is not None
    return ("changelog_entry", "pass" if has_entry else "fail")


def _check_release_workflow(repo_root: Path) -> tuple[str, str]:
    workflow = repo_root / ".github/workflows/release.yml"
    if not workflow.exists():
        return ("release_workflow", "fail")
    text = workflow.read_text(encoding="utf-8")
    required_markers = (
        "tools/release/checklist.py",
        "tools/release/changelog.py",
    )
    ok = all(marker in text for marker in required_markers)
    return ("release_workflow", "pass" if ok else "fail")


def _render_text(result: ChecklistResult) -> str:
    lines = [f"GA checklist: {'PASS' if result.ok else 'FAIL'}"]
    for name, status in result.checks:
        lines.append(f"- {name}: {status}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run deterministic GA release checklist checks.")
    parser.add_argument("--json", action="store_true", help="Emit checklist report as canonical JSON.")
    args = parser.parse_args(argv)
    repo_root = Path(__file__).resolve().parents[2]
    result = run_checklist(repo_root)
    if args.json:
        print(canonical_json_dumps(result.as_dict(), pretty=True, drop_run_keys=False))
    else:
        print(_render_text(result))
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
