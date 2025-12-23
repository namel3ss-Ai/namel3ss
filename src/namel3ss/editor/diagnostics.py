from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

from namel3ss.errors.base import Namel3ssError
from namel3ss.lint.engine import lint_project, lint_source
from namel3ss.lint.types import Finding
from namel3ss.module_loader.types import ProjectLoadResult
from namel3ss.editor.workspace import EditorWorkspace, collect_project_files, normalize_path
from namel3ss.governance.verify import _flow_mutates, _page_has_form


@dataclass(frozen=True)
class Diagnostic:
    id: str
    severity: str
    message: str
    file: str | None
    line: int | None
    column: int | None
    what: str
    why: str
    fix: str
    example: str

    def to_dict(self) -> dict:
        payload = {
            "id": self.id,
            "severity": self.severity,
            "message": self.message,
            "what": self.what,
            "why": self.why,
            "fix": self.fix,
            "example": self.example,
        }
        if self.file:
            payload["file"] = self.file
        if self.line is not None:
            payload["line"] = self.line
        if self.column is not None:
            payload["column"] = self.column
        return payload


def diagnose(workspace: EditorWorkspace, *, overrides: dict[Path, str] | None = None) -> list[Diagnostic]:
    try:
        project = workspace.load(overrides)
    except Namel3ssError as err:
        diagnostics = [_diagnostic_from_error(err, workspace)]
        diagnostics.extend(_fallback_lint(workspace, overrides))
        return _sort(diagnostics)

    diagnostics = [_diagnostic_from_finding(f, workspace.root) for f in lint_project(project)]
    diagnostics.extend(_missing_requires(project, workspace.root))
    return _sort(diagnostics)


def _missing_requires(project: ProjectLoadResult, root: Path) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    flows = [flow for flow in project.program.flows if _flow_mutates(flow)]
    for flow in flows:
        if flow.requires is None:
            flow_name = flow.name.split(".", 1)[1] if "." in flow.name else flow.name
            diagnostics.append(
                Diagnostic(
                    id=f"governance.requires_flow_missing:{flow_name}",
                    severity="warning",
                    message=f'Flow "{flow_name}" mutates data without requires.',
                    file=_best_file_for_name(project, flow_name, kind="flow", root=root),
                    line=flow.line,
                    column=flow.column,
                    what="Flow mutates data without requires.",
                    why="Mutating flows should be gated by an access rule.",
                    fix='Add a requires clause to the flow header.',
                    example='flow "update_order": requires identity.role is "admin"',
                )
            )
    for page in project.program.pages:
        if _page_has_form(page) and page.requires is None:
            page_name = page.name.split(".", 1)[1] if "." in page.name else page.name
            diagnostics.append(
                Diagnostic(
                    id=f"governance.requires_page_missing:{page_name}",
                    severity="warning",
                    message=f'Page "{page_name}" has a form without requires.',
                    file=_best_file_for_name(project, page_name, kind="page", root=root),
                    line=page.line,
                    column=page.column,
                    what="Page form is missing requires.",
                    why="Forms mutate data and should be protected.",
                    fix='Add a requires clause to the page header.',
                    example='page "home": requires identity.role is "admin"',
                )
            )
    return diagnostics


def _best_file_for_name(project: ProjectLoadResult, name: str, *, kind: str, root: Path) -> str | None:
    local_name = name.split(".", 1)[1] if "." in name else name
    for path, source in project.sources.items():
        if f'{kind} "{local_name}"' in source:
            return normalize_path(path, root)
    return normalize_path(project.app_path, root)


def _fallback_lint(workspace: EditorWorkspace, overrides: dict[Path, str] | None) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for path in collect_project_files(workspace.root):
        source = None
        if overrides and path in overrides:
            source = overrides[path]
        else:
            try:
                source = path.read_text(encoding="utf-8")
            except FileNotFoundError:
                continue
        for finding in lint_source(source):
            diagnostics.append(_diagnostic_from_finding(finding, workspace.root, path))
    return diagnostics


def _diagnostic_from_error(err: Namel3ssError, workspace: EditorWorkspace) -> Diagnostic:
    what, why, fix, example = _parse_guidance(err.message)
    file_hint = None
    if err.details and "file" in err.details:
        file_hint = normalize_path(Path(str(err.details["file"])), workspace.root)
    message = what or err.message.splitlines()[0]
    diag_id = "error.namel3ss"
    if err.details and {"module", "kind", "name"} <= set(err.details.keys()):
        module = str(err.details.get("module"))
        kind = str(err.details.get("kind"))
        name = str(err.details.get("name"))
        diag_id = f"module.missing_export:{module}:{kind}:{name}"
    return Diagnostic(
        id=diag_id,
        severity="error",
        message=message,
        file=file_hint,
        line=err.line,
        column=err.column,
        what=what or message,
        why=why or "The source could not be parsed or resolved.",
        fix=fix or "Fix the highlighted issue and retry.",
        example=example or 'flow "demo":\n  return "ok"',
    )


def _diagnostic_from_finding(finding: Finding, root: Path, file_path: Path | None = None) -> Diagnostic:
    what = finding.message
    return Diagnostic(
        id=finding.code,
        severity=finding.severity,
        message=finding.message,
        file=normalize_path(file_path or Path(finding.file), root) if (finding.file or file_path) else None,
        line=finding.line,
        column=finding.column,
        what=what,
        why="The checker flagged a potential issue.",
        fix="Review the highlighted line.",
        example='flow "demo":\n  return "ok"',
    )


def _parse_guidance(message: str) -> tuple[str, str, str, str]:
    what = ""
    why = ""
    fix = ""
    example = ""
    for line in message.splitlines():
        if line.startswith("What happened:"):
            what = line.split("What happened:", 1)[1].strip()
        elif line.startswith("Why:"):
            why = line.split("Why:", 1)[1].strip()
        elif line.startswith("Fix:"):
            fix = line.split("Fix:", 1)[1].strip()
        elif line.startswith("Example:"):
            example = line.split("Example:", 1)[1].strip()
    return what, why, fix, example


def _sort(diagnostics: Iterable[Diagnostic]) -> list[Diagnostic]:
    return sorted(
        diagnostics,
        key=lambda d: (
            d.file or "",
            d.line or 0,
            d.column or 0,
            d.id,
        ),
    )


__all__ = ["Diagnostic", "diagnose"]
