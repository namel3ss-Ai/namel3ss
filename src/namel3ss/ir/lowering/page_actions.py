from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError


def _validate_overlay_action(
    action: ast.CardAction | ast.TableRowAction | ast.ListAction,
    overlays: dict[str, set[str]],
    page_name: str,
) -> None:
    if action.target is None:
        raise Namel3ssError(
            f"Page '{page_name}' action '{action.label}' requires a modal or drawer target",
            line=action.line,
            column=action.column,
        )
    if action.kind in {"open_modal", "close_modal"}:
        if action.target not in overlays.get("modal", set()):
            raise Namel3ssError(
                f"Page '{page_name}' references unknown modal '{action.target}'",
                line=action.line,
                column=action.column,
            )
        return
    if action.kind in {"open_drawer", "close_drawer"}:
        if action.target not in overlays.get("drawer", set()):
            raise Namel3ssError(
                f"Page '{page_name}' references unknown drawer '{action.target}'",
                line=action.line,
                column=action.column,
            )
        return
    raise Namel3ssError(
        f"Page '{page_name}' action '{action.label}' is not supported",
        line=action.line,
        column=action.column,
    )


__all__ = ["_validate_overlay_action"]
