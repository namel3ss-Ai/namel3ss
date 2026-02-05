from __future__ import annotations

from namel3ss.lint.types import Finding


def lint_crud(ast_program, *, strict: bool, record_names: set[str] | None = None) -> list[Finding]:
    crud_defs = list(getattr(ast_program, "crud", []) or [])
    if not crud_defs:
        return []
    if record_names is None:
        record_names = {record.name for record in getattr(ast_program, "records", [])}
    findings: list[Finding] = []
    seen: set[str] = set()
    for crud in crud_defs:
        record_name = crud.record_name
        if record_name in seen:
            findings.append(
                Finding(
                    code="crud.duplicate",
                    message=f'Crud for "{record_name}" is declared more than once.',
                    line=crud.line,
                    column=crud.column,
                    severity="error",
                )
            )
        seen.add(record_name)
        if record_name not in record_names:
            findings.append(
                Finding(
                    code="crud.unknown_record",
                    message=f'Crud references unknown record "{record_name}".',
                    line=crud.line,
                    column=crud.column,
                    severity="error" if strict else "warning",
                )
            )
    return findings


__all__ = ["lint_crud"]
