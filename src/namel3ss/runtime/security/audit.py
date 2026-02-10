from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from namel3ss.errors.base import Namel3ssError
from namel3ss.i18n.translation_loader import load_translation_bundle
from namel3ss.ui.plugins.loader import load_plugin_schema, resolve_plugin_directories
from namel3ss.ui.plugins.sandbox import load_sandboxed_renderer

_SCRIPT_TOKENS: tuple[str, ...] = ("<script", "javascript:")
_ALLOWED_THEME_SCALARS = (str, int, float, bool)


@dataclass(frozen=True)
class SecurityAuditFinding:
    code: str
    severity: str
    message: str
    path: str | None = None
    line: int | None = None

    def as_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
        }
        if self.path is not None:
            payload["path"] = self.path
        if self.line is not None:
            payload["line"] = self.line
        return payload


@dataclass(frozen=True)
class SecurityAuditReport:
    findings: tuple[SecurityAuditFinding, ...]

    @property
    def error_count(self) -> int:
        return sum(1 for item in self.findings if item.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for item in self.findings if item.severity == "warning")

    def as_dict(self) -> dict[str, object]:
        return {
            "status": "pass" if not self.findings else "fail",
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "findings": [item.as_dict() for item in self.findings],
        }


def run_security_audit(
    *,
    project_root: str | Path,
    app_path: str | Path | None = None,
    plugin_names: Sequence[str] = (),
    translation_files: Sequence[str | Path] = (),
    theme_overrides: Mapping[str, object] | None = None,
) -> SecurityAuditReport:
    root = Path(project_root).expanduser().resolve()
    findings: list[SecurityAuditFinding] = []
    findings.extend(_audit_plugins(root, app_path=app_path, plugin_names=plugin_names))
    findings.extend(_audit_translations(root, translation_files=translation_files))
    findings.extend(_audit_theme_overrides(theme_overrides or {}))
    ordered = tuple(sorted(findings, key=_finding_sort_key))
    return SecurityAuditReport(findings=ordered)


def enforce_security_audit(report: SecurityAuditReport) -> None:
    if report.error_count == 0:
        return
    first = report.findings[0]
    raise Namel3ssError(
        f"Security audit failed with {report.error_count} error(s). First issue: {first.code}: {first.message}"
    )


def _audit_plugins(
    project_root: Path,
    *,
    app_path: str | Path | None,
    plugin_names: Sequence[str],
) -> list[SecurityAuditFinding]:
    findings: list[SecurityAuditFinding] = []
    names = sorted({str(name).strip() for name in plugin_names if str(name).strip()})
    if not names:
        return findings
    directories = resolve_plugin_directories(project_root=project_root, app_path=app_path)
    for name in names:
        try:
            schema = load_plugin_schema(name, directories=directories)
        except Exception as err:
            findings.append(
                SecurityAuditFinding(
                    code="plugin_manifest_error",
                    severity="error",
                    message=str(err),
                    path=name,
                )
            )
            continue

        if "legacy_full_access" in set(schema.permissions):
            findings.append(
                SecurityAuditFinding(
                    code="plugin_permission_legacy_full_access",
                    severity="warning",
                    message=f"Plugin '{schema.name}' requests legacy_full_access permission.",
                    path=(schema.plugin_root / "plugin.json").as_posix(),
                )
            )
        if schema.components:
            findings.extend(_audit_plugin_renderer(schema.module_path))
    return findings


def _audit_plugin_renderer(module_path: Path) -> list[SecurityAuditFinding]:
    try:
        load_sandboxed_renderer(module_path)
    except Exception as err:
        line = getattr(err, "line", None)
        return [
            SecurityAuditFinding(
                code="plugin_renderer_violation",
                severity="error",
                message=str(err),
                path=module_path.as_posix(),
                line=int(line) if isinstance(line, int) else None,
            )
        ]
    return []


def _audit_translations(
    project_root: Path,
    *,
    translation_files: Sequence[str | Path],
) -> list[SecurityAuditFinding]:
    findings: list[SecurityAuditFinding] = []
    files = _resolve_translation_files(project_root, translation_files)
    for path in files:
        try:
            bundle = load_translation_bundle(path)
        except Exception as err:
            findings.append(
                SecurityAuditFinding(
                    code="translation_bundle_error",
                    severity="error",
                    message=str(err),
                    path=path.as_posix(),
                )
            )
            continue
        for key in sorted(bundle.messages.keys()):
            text = bundle.messages[key]
            token = _script_token(text)
            if token is None:
                continue
            findings.append(
                SecurityAuditFinding(
                    code="translation_injection_pattern",
                    severity="error",
                    message=f"Message '{key}' contains forbidden token '{token}'.",
                    path=path.as_posix(),
                )
            )
    return findings


def _resolve_translation_files(project_root: Path, files: Sequence[str | Path]) -> tuple[Path, ...]:
    if files:
        resolved = tuple(sorted({Path(item).expanduser().resolve() for item in files}))
        return resolved
    default_root = project_root / "i18n" / "locales"
    if not default_root.exists():
        return tuple()
    return tuple(sorted(path.resolve() for path in default_root.rglob("*.json") if path.is_file()))


def _audit_theme_overrides(theme_overrides: Mapping[str, object]) -> list[SecurityAuditFinding]:
    findings: list[SecurityAuditFinding] = []
    for key in sorted(str(item) for item in theme_overrides.keys()):
        original_key = _resolve_original_key(theme_overrides, key)
        if original_key is None:
            continue
        value = theme_overrides[original_key]
        if not isinstance(value, _ALLOWED_THEME_SCALARS):
            findings.append(
                SecurityAuditFinding(
                    code="theme_override_type",
                    severity="error",
                    message=f"Theme override '{key}' must be a scalar value.",
                )
            )
            continue
        if isinstance(value, str):
            text = value.strip().lower()
            if "{" in text or "}" in text or ";" in text or _script_token(text):
                findings.append(
                    SecurityAuditFinding(
                        code="theme_override_injection_pattern",
                        severity="error",
                        message=f"Theme override '{key}' contains unsupported characters.",
                    )
                )
    return findings


def _script_token(value: str) -> str | None:
    lowered = value.lower()
    for token in _SCRIPT_TOKENS:
        if token in lowered:
            return token
    return None


def _resolve_original_key(mapping: Mapping[str, object], key_text: str) -> str | None:
    for key in mapping.keys():
        if str(key) == key_text:
            return key
    return None


def _finding_sort_key(item: SecurityAuditFinding) -> tuple[object, ...]:
    severity_order = 0 if item.severity == "error" else 1
    return (
        severity_order,
        item.code,
        item.path or "",
        item.line or 0,
        item.message,
    )


__all__ = [
    "SecurityAuditFinding",
    "SecurityAuditReport",
    "enforce_security_audit",
    "run_security_audit",
]
