from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError


def _validate_overlay_action(
    action: ast.CardAction | ast.TableRowAction | ast.ListAction,
    overlays: dict[str, set[str]],
    page_name: str,
    page_names: set[str],
) -> None:
    if action.kind in {"open_modal", "close_modal"}:
        if action.target is None:
            raise Namel3ssError(
                f"Page '{page_name}' action '{action.label}' requires a modal target",
                line=action.line,
                column=action.column,
            )
        if action.target not in overlays.get("modal", set()):
            raise Namel3ssError(
                f"Page '{page_name}' references unknown modal '{action.target}'",
                line=action.line,
                column=action.column,
            )
        return
    if action.kind in {"open_drawer", "close_drawer"}:
        if action.target is None:
            raise Namel3ssError(
                f"Page '{page_name}' action '{action.label}' requires a drawer target",
                line=action.line,
                column=action.column,
            )
        if action.target not in overlays.get("drawer", set()):
            raise Namel3ssError(
                f"Page '{page_name}' references unknown drawer '{action.target}'",
                line=action.line,
                column=action.column,
            )
        return
    if action.kind == "navigate_to":
        if action.target is None:
            raise Namel3ssError(
                f"Page '{page_name}' action '{action.label}' requires a target page",
                line=action.line,
                column=action.column,
            )
        if action.target not in page_names:
            raise Namel3ssError(
                f"Page '{page_name}' action '{action.label}' references unknown page '{action.target}'",
                line=action.line,
                column=action.column,
            )
        return
    if action.kind == "go_back":
        return
    raise Namel3ssError(
        f"Page '{page_name}' action '{action.label}' is not supported",
        line=action.line,
        column=action.column,
    )


__all__ = ["_validate_overlay_action"]
