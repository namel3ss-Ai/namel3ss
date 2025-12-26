from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.governance.verify import run_verify
from namel3ss.module_loader import load_project
from namel3ss.parser.core import parse
from namel3ss.pkg.checksums import verify_checksums
from namel3ss.pkg.install import FetchSession
from namel3ss.pkg.metadata import load_metadata
from namel3ss.pkg.specs import parse_source_spec


FORBIDDEN_SCRIPT_KEYS = {
    "postinstall",
    "preinstall",
    "install",
    "prepare",
}


@dataclass(frozen=True)
class ValidationIssue:
    severity: str
    message: str
    path: str | None = None

    def to_dict(self) -> dict:
        payload = {"severity": self.severity, "message": self.message}
        if self.path:
            payload["path"] = self.path
        return payload


@dataclass(frozen=True)
class ValidationReport:
    root: str
    status: str
    issues: list[ValidationIssue]

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "root": self.root,
            "issues": [issue.to_dict() for issue in self.issues],
        }


def validate_package(target: str, *, strict: bool) -> ValidationReport:
    root, cleanup = _resolve_target(Path(target))
    try:
        issues = _validate_root(root, strict=strict)
    finally:
        if cleanup:
            cleanup()
    status = "ok" if not _has_errors(issues) else "fail"
    return ValidationReport(root=root.as_posix(), status=status, issues=issues)


def _resolve_target(path: Path) -> tuple[Path, callable | None]:
    raw = str(path)
    if raw.startswith("github:"):
        session = FetchSession()
        source = parse_source_spec(raw)
        root = session.fetch(source)
        return root, session.close
    resolved = path.resolve()
    if not resolved.exists():
        raise Namel3ssError(
            build_guidance_message(
                what="Package path was not found.",
                why=f"Expected {resolved.as_posix()} to exist.",
                fix="Provide a valid package path or GitHub source.",
                example="n3 pkg validate .",
            )
        )
    return resolved, None


def _validate_root(root: Path, *, strict: bool) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    capsule_path = root / "capsule.ai"
    if not capsule_path.exists():
        issues.append(_error("capsule.ai is missing.", capsule_path))
    else:
        issues.extend(_validate_capsule(capsule_path))

    metadata = None
    try:
        metadata = load_metadata(root)
    except Namel3ssError as err:
        issues.append(_error(str(err), root / "namel3ss.package.json"))

    readme_path = root / "README.md"
    if not readme_path.exists():
        issues.append(_error("README.md is missing.", readme_path))
    else:
        text = readme_path.read_text(encoding="utf-8").strip()
        if len(text) < 20:
            issues.append(_warn("README.md is too short; add a usage summary.", readme_path, strict=strict))

    license_path = root / "LICENSE"
    if not license_path.exists():
        issues.append(_error("LICENSE file is required.", license_path))
    if metadata and metadata.license_file and metadata.license_file != "LICENSE":
        issues.append(
            _error(
                "License file must be LICENSE to match metadata.",
                root / metadata.license_file,
            )
        )

    if metadata:
        try:
            verify_checksums(root, root / metadata.checksums_file)
        except Namel3ssError as err:
            issues.append(_error(str(err), root / metadata.checksums_file))

    issues.extend(_scan_forbidden_scripts(root))
    issues.extend(_check_docs_hint(readme_path, root, strict=strict))
    issues.extend(_verify_examples(root))
    return issues


def _validate_capsule(path: Path) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    try:
        program = parse(path.read_text(encoding="utf-8"), allow_capsule=True)
    except Namel3ssError as err:
        issues.append(_error(str(err), path))
        return issues
    capsule = program.capsule
    if capsule is None:
        issues.append(_error("capsule.ai must declare a capsule block.", path))
        return issues
    if not capsule.exports:
        issues.append(_error("Capsule exports must be explicit and non-empty.", path))
    return issues


def _scan_forbidden_scripts(root: Path) -> list[ValidationIssue]:
    package_json = root / "package.json"
    if not package_json.exists():
        return []
    try:
        data = json.loads(package_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return [_error("package.json is not valid JSON.", package_json)]
    scripts = data.get("scripts") if isinstance(data, dict) else None
    if not isinstance(scripts, dict):
        return []
    issues: list[ValidationIssue] = []
    for key in FORBIDDEN_SCRIPT_KEYS:
        if key in scripts:
            issues.append(_error(f"Forbidden install script: {key}.", package_json))
    return issues


def _check_docs_hint(readme_path: Path, root: Path, *, strict: bool) -> list[ValidationIssue]:
    docs_dir = root / "docs"
    if docs_dir.exists():
        return []
    if not readme_path.exists():
        return []
    text = readme_path.read_text(encoding="utf-8").lower()
    if "docs" in text:
        return []
    return [_warn("Add a docs link or docs/ folder (recommended).", readme_path, strict=strict)]


def _verify_examples(root: Path) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for folder in ("examples", "example"):
        candidate = root / folder / "app.ai"
        if not candidate.exists():
            continue
        try:
            project = load_project(candidate)
        except Namel3ssError as err:
            issues.append(_error(str(err), candidate))
            continue
        report = run_verify(
            project.app_path,
            target="local",
            prod=True,
            config_root=project.app_path.parent,
            project_root_override=project.app_path.parent,
        )
        if report.get("status") != "ok":
            issues.append(_error("Example app failed verify --prod.", candidate))
    return issues


def _error(message: str, path: Path | None) -> ValidationIssue:
    return ValidationIssue(severity="error", message=message, path=path.as_posix() if path else None)


def _warn(message: str, path: Path | None, *, strict: bool) -> ValidationIssue:
    severity = "error" if strict else "warn"
    return ValidationIssue(severity=severity, message=message, path=path.as_posix() if path else None)


def _has_errors(issues: list[ValidationIssue]) -> bool:
    return any(issue.severity == "error" for issue in issues)


__all__ = ["ValidationIssue", "ValidationReport", "validate_package"]
