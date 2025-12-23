from __future__ import annotations

from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.lint.engine import lint_project
from namel3ss.lint.types import Finding
from namel3ss.module_loader import load_project
from namel3ss.utils.json_tools import dumps_pretty


def run_lint(path_str: str, check_only: bool, strict: bool = True, allow_legacy_type_aliases: bool = True) -> int:
    path = Path(path_str)
    if path.suffix != ".ai":
        raise Namel3ssError("Input file must have .ai extension")
    try:
        project = load_project(path, allow_legacy_type_aliases=allow_legacy_type_aliases)
        findings = lint_project(project, strict=strict)
    except Namel3ssError as err:
        file_path = None
        details = getattr(err, "details", None) or {}
        if isinstance(details, dict):
            file_path = details.get("file")
        findings = [
            Finding(
                code="lint.parse_failed",
                message=str(err),
                line=err.line,
                column=err.column,
                severity="warning",
                file=file_path,
            )
        ]
    output = {
        "ok": len(findings) == 0,
        "count": len(findings),
        "findings": [f.to_dict() for f in findings],
    }
    print(dumps_pretty(output))
    if check_only and findings:
        return 1
    return 0
