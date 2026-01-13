from __future__ import annotations

from namel3ss.config.loader import load_config
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.render import format_error
from namel3ss.lint.engine import lint_project
from namel3ss.module_loader import load_project
from namel3ss.cli.text_output import prepare_cli_text
from namel3ss.runtime.identity.context import resolve_identity
from namel3ss.ui.manifest import build_manifest
from namel3ss.validation import ValidationMode, ValidationWarning


def run_check(path: str, allow_legacy_type_aliases: bool = True) -> int:
    sections: list[str] = []
    warnings: list[ValidationWarning] = []
    try:
        project = load_project(path, allow_legacy_type_aliases=allow_legacy_type_aliases)
        program_ir = project.program
        sources = project.sources
        sections.append("Parse: OK")
    except Namel3ssError as err:
        sections.append(f"Parse: FAIL\n{prepare_cli_text(format_error(err, locals().get('sources', '')))}")
        print("\n".join(sections))
        return 1

    findings = lint_project(project)
    if findings:
        sections.append(f"Lint: FAIL {len(findings)} findings")
        for f in findings:
            location = ""
            if f.line:
                location = f" line {f.line}"
                if f.column:
                    location += f" col {f.column}"
            sections.append(f"- {f.code} {f.severity} {f.message}{location}")
        sections.append("Fix: run `n3 app.ai format` or address the findings above, then re-run `n3 app.ai lint`.")
    else:
        sections.append("Lint: OK")

    manifest = None
    try:
        config = load_config(app_path=project.app_path, root=project.app_path.parent)
        identity = resolve_identity(
            config,
            getattr(program_ir, "identity", None),
            mode=ValidationMode.STATIC,
            warnings=warnings,
        )
        manifest = build_manifest(
            program_ir,
            state={},
            store=None,
            identity=identity,
            mode=ValidationMode.STATIC,
            warnings=warnings,
        )
        sections.append("Manifest: OK")
    except Namel3ssError as err:
        sections.append(f"Manifest: FAIL\n{prepare_cli_text(format_error(err, sources))}")

    if manifest and manifest.get("actions") is not None:
        sections.append(f"Actions: {len(manifest.get('actions', {}))} discovered")
    if warnings:
        sections.append(f"Warnings: {len(warnings)}")
        for warn in warnings:
            runtime_note = " (enforced at runtime)" if getattr(warn, "enforced_at", None) else ""
            category = f"[{warn.category}]" if getattr(warn, "category", None) else ""
            sections.append(f"- WARN {category} {warn.message}{runtime_note}".rstrip())

    print("\n".join(sections))
    success = all("FAIL" not in line for line in sections)
    return 0 if success else 1
