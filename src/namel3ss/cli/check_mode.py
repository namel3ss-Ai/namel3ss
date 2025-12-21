from __future__ import annotations

from namel3ss.cli.app_loader import load_program
from namel3ss.cli.json_io import dumps_pretty
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.render import format_error
from namel3ss.lint.engine import lint_source
from namel3ss.runtime.store.memory_store import MemoryStore
from namel3ss.ui.manifest import build_manifest


def run_check(path: str) -> int:
    sections: list[str] = []
    try:
        program_ir, source = load_program(path)
        sections.append("Parse: OK")
    except Namel3ssError as err:
        sections.append(f"Parse: FAIL\n{format_error(err, locals().get('source', ''))}")
        print("\n".join(sections))
        return 1

    findings = lint_source(source)
    if findings:
        sections.append(f"Lint: FAIL ({len(findings)} findings)")
        for f in findings:
            sections.append(f"- {f.code} {f.severity} {f.message} ({f.line}:{f.column})")
    else:
        sections.append("Lint: OK")

    manifest = None
    try:
        manifest = build_manifest(program_ir, state={}, store=MemoryStore())
        sections.append("Manifest: OK")
    except Namel3ssError as err:
        sections.append(f"Manifest: FAIL\n{format_error(err, source)}")

    if manifest and manifest.get("actions") is not None:
        sections.append(f"Actions: {len(manifest.get('actions', {}))} discovered")

    print("\n".join(sections))
    success = all("FAIL" not in line for line in sections)
    return 0 if success else 1
