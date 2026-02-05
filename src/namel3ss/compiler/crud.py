from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message


def validate_crud(crud_defs: list[ast.CrudDefinition], *, record_names: set[str]) -> None:
    seen: set[str] = set()
    for crud in crud_defs:
        record_name = crud.record_name
        if record_name in seen:
            raise Namel3ssError(
                build_guidance_message(
                    what=f'Crud for "{record_name}" is declared more than once.',
                    why="Each record may only have one crud declaration.",
                    fix="Remove the duplicate crud line.",
                    example=f'crud "{record_name}"',
                ),
                line=crud.line,
                column=crud.column,
            )
        seen.add(record_name)
        if record_name not in record_names:
            raise Namel3ssError(
                build_guidance_message(
                    what=f'Crud references unknown record "{record_name}".',
                    why="Crud can only target records that are defined.",
                    fix="Add the record declaration or update the crud name.",
                    example=f'record "{record_name}":',
                ),
                line=crud.line,
                column=crud.column,
            )


__all__ = ["validate_crud"]
