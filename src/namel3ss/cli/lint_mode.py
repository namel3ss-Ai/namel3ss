from __future__ import annotations

from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.render import format_error
from namel3ss.lint.engine import lint_source


def run_lint(path_str: str, check_only: bool) -> int:
    path = Path(path_str)
    if path.suffix != ".ai":
        raise Namel3ssError("Input file must have .ai extension")
    try:
        source = path.read_text(encoding="utf-8")
    except FileNotFoundError as err:
        raise Namel3ssError(f"File not found: {path}") from err
    findings = lint_source(source)
    output = {
        "ok": len(findings) == 0,
        "count": len(findings),
        "findings": [f.to_dict() for f in findings],
    }
    import json

    print(json.dumps(output, indent=2, ensure_ascii=False))
    if check_only and findings:
        return 1
    return 0
