from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir
from namel3ss.ir.model.ui_state import iter_ui_state_fields


PERMISSION_DOMAIN_ACTIONS: dict[str, tuple[str, ...]] = {
    "ai": ("call", "tools"),
    "uploads": ("read", "write"),
    "ui_state": ("persistent_write",),
    "navigation": ("change_page",),
}
PERMISSION_KEYS: tuple[str, ...] = tuple(
    sorted(f"{domain}.{action}" for domain, actions in PERMISSION_DOMAIN_ACTIONS.items() for action in actions)
)
LEGACY_MODE_WARNING = (
    "App permissions are not declared. Legacy permissive mode is active; declare a permissions block to enforce "
    "governance boundaries."
)


@dataclass(frozen=True)
class PermissionUse:
    permission: str
    reason: str
    line: int | None
    column: int | None

    def as_dict(self) -> dict[str, object]:
        return {
            "permission": self.permission,
            "reason": self.reason,
            "line": self.line,
            "column": self.column,
        }


@dataclass(frozen=True)
class AppPermissionsValidationResult:
    enabled: bool
    matrix: dict[str, bool]
    usage: list[dict[str, object]]
    warnings: list[str]


def build_permission_matrix(declaration: ast.AppPermissionsDecl | None) -> tuple[dict[str, bool], bool]:
    if declaration is None:
        # Legacy mode: runtime keeps existing behavior unless explicit permissions are declared.
        return {key: True for key in PERMISSION_KEYS}, False
    matrix = {key: False for key in PERMISSION_KEYS}
    for domain in getattr(declaration, "domains", []) or []:
        domain_name = str(getattr(domain, "domain", "") or "")
        allowed_actions = PERMISSION_DOMAIN_ACTIONS.get(domain_name)
        if allowed_actions is None:
            raise Namel3ssError(
                f"Unknown permissions domain '{domain_name}'.",
                line=getattr(domain, "line", None),
                column=getattr(domain, "column", None),
            )
        for action in getattr(domain, "actions", []) or []:
            action_name = str(getattr(action, "action", "") or "")
            if action_name not in set(allowed_actions):
                allowed_text = ", ".join(sorted(allowed_actions))
                raise Namel3ssError(
                    f"Unknown permissions action '{domain_name}.{action_name}'. Allowed actions: {allowed_text}.",
                    line=getattr(action, "line", None),
                    column=getattr(action, "column", None),
                )
            matrix[f"{domain_name}.{action_name}"] = bool(getattr(action, "allowed", False))
    return matrix, True


def build_ui_state_scope_map(declaration: ir.UIStateDecl | None) -> dict[str, str]:
    if declaration is None:
        return {}
    scope_by_key: dict[str, str] = {}
    for scope, field in iter_ui_state_fields(declaration):
        key = str(getattr(field, "key", "") or "")
        if key:
            scope_by_key[key] = scope
    return scope_by_key


def validate_app_permissions(
    *,
    program: ir.Program,
    declaration: ast.AppPermissionsDecl | None,
    capabilities: tuple[str, ...],
    ai_profiles: dict[str, ir.AIDecl],
    ui_state_declaration: ir.UIStateDecl | None,
) -> AppPermissionsValidationResult:
    matrix, enabled = build_permission_matrix(declaration)
    if enabled and "app_permissions" not in set(capabilities or ()):  # compile-time gate
        raise Namel3ssError(
            "Permissions require capability app_permissions. Add 'app_permissions' to the capabilities list.",
            line=getattr(declaration, "line", None),
            column=getattr(declaration, "column", None),
        )

    ui_state_scope_by_key = build_ui_state_scope_map(ui_state_declaration)
    usage = _collect_permission_usage(
        program=program,
        ai_profiles=ai_profiles,
        ui_state_scope_by_key=ui_state_scope_by_key,
    )

    if enabled:
        for entry in usage:
            if matrix.get(entry.permission, False):
                continue
            raise Namel3ssError(
                _denied_permission_message(entry.permission, entry.reason),
                line=entry.line,
                column=entry.column,
            )

    warnings: list[str] = []
    if enabled:
        used_permissions = {entry.permission for entry in usage}
        for key in PERMISSION_KEYS:
            if matrix.get(key, False) and key not in used_permissions:
                warnings.append(f"Permission '{key}' is allowed but unused.")
    elif usage:
        warnings.append(LEGACY_MODE_WARNING)

    usage_rows = [entry.as_dict() for entry in usage]
    return AppPermissionsValidationResult(
        enabled=enabled,
        matrix={key: bool(matrix.get(key, False)) for key in PERMISSION_KEYS},
        usage=usage_rows,
        warnings=warnings,
    )


def _denied_permission_message(permission: str, reason: str) -> str:
    domain, action = permission.split(".", 1)
    return (
        f"Permission '{permission}' is denied but required for {reason}. "
        f"Set permissions:\n  {domain}:\n    {action}: allowed"
    )


def _collect_permission_usage(
    *,
    program: ir.Program,
    ai_profiles: dict[str, ir.AIDecl],
    ui_state_scope_by_key: dict[str, str],
) -> list[PermissionUse]:
    uses: list[PermissionUse] = []

    for flow in getattr(program, "flows", []) or []:
        for stmt in _walk_dataclass_nodes(getattr(flow, "body", []) or []):
            if isinstance(stmt, ir.AskAIStmt):
                uses.append(
                    PermissionUse(
                        permission="ai.call",
                        reason=f'flow "{flow.name}" ask-ai statement',
                        line=stmt.line,
                        column=stmt.column,
                    )
                )
                profile = ai_profiles.get(stmt.ai_name)
                if profile is not None and list(getattr(profile, "exposed_tools", []) or []):
                    uses.append(
                        PermissionUse(
                            permission="ai.tools",
                            reason=f'flow "{flow.name}" ask-ai tool usage',
                            line=stmt.line,
                            column=stmt.column,
                        )
                    )
                continue
            if isinstance(stmt, ir.Set):
                key = _state_ui_key(getattr(stmt, "target", None))
                if key and ui_state_scope_by_key.get(key) == "persistent":
                    uses.append(
                        PermissionUse(
                            permission="ui_state.persistent_write",
                            reason=f'flow "{flow.name}" persistent state write',
                            line=stmt.line,
                            column=stmt.column,
                        )
                    )
                continue
            if isinstance(stmt, ir.OrderList):
                key = _state_ui_key(getattr(stmt, "target", None))
                if key and ui_state_scope_by_key.get(key) == "persistent":
                    uses.append(
                        PermissionUse(
                            permission="ui_state.persistent_write",
                            reason=f'flow "{flow.name}" persistent state reorder',
                            line=stmt.line,
                            column=stmt.column,
                        )
                    )

    global_navigation = getattr(program, "ui_navigation", None)
    if global_navigation is not None:
        uses.append(
            PermissionUse(
                permission="navigation.change_page",
                reason="declared nav_sidebar",
                line=getattr(global_navigation, "line", None),
                column=getattr(global_navigation, "column", None),
            )
        )

    for page in getattr(program, "pages", []) or []:
        page_navigation = getattr(page, "ui_navigation", None)
        if page_navigation is not None:
            uses.append(
                PermissionUse(
                    permission="navigation.change_page",
                    reason=f'page "{page.name}" nav_sidebar',
                    line=getattr(page_navigation, "line", None),
                    column=getattr(page_navigation, "column", None),
                )
            )
        for item in _walk_page_items(page):
            if isinstance(item, ir.ButtonItem):
                action_kind = str(getattr(item, "action_kind", "call_flow") or "call_flow")
                if action_kind in {"navigate_to", "go_back"}:
                    uses.append(
                        PermissionUse(
                            permission="navigation.change_page",
                            reason=f'page "{page.name}" button navigation',
                            line=item.line,
                            column=item.column,
                        )
                    )
            elif isinstance(item, ir.LinkItem):
                uses.append(
                    PermissionUse(
                        permission="navigation.change_page",
                        reason=f'page "{page.name}" link navigation',
                        line=item.line,
                        column=item.column,
                    )
                )
            elif isinstance(item, ir.CardItem):
                for action in list(getattr(item, "actions", []) or []):
                    if action.kind in {"navigate_to", "go_back"}:
                        uses.append(
                            PermissionUse(
                                permission="navigation.change_page",
                                reason=f'page "{page.name}" card action navigation',
                                line=action.line,
                                column=action.column,
                            )
                        )
            elif isinstance(item, ir.ListItem):
                for action in list(getattr(item, "actions", []) or []):
                    if action.kind in {"navigate_to", "go_back"}:
                        uses.append(
                            PermissionUse(
                                permission="navigation.change_page",
                                reason=f'page "{page.name}" list action navigation',
                                line=action.line,
                                column=action.column,
                            )
                        )
            elif isinstance(item, ir.TableItem):
                for action in list(getattr(item, "row_actions", []) or []):
                    if action.kind in {"navigate_to", "go_back"}:
                        uses.append(
                            PermissionUse(
                                permission="navigation.change_page",
                                reason=f'page "{page.name}" table action navigation',
                                line=action.line,
                                column=action.column,
                            )
                        )
            elif isinstance(item, ir.UploadItem):
                uses.append(
                    PermissionUse(
                        permission="uploads.write",
                        reason=f'page "{page.name}" upload control',
                        line=item.line,
                        column=item.column,
                    )
                )
                uses.append(
                    PermissionUse(
                        permission="uploads.read",
                        reason=f'page "{page.name}" upload control',
                        line=item.line,
                        column=item.column,
                    )
                )
            elif isinstance(item, (ir.SourcePreviewItem, ir.ScopeSelectorItem)):
                uses.append(
                    PermissionUse(
                        permission="uploads.read",
                        reason=f'page "{page.name}" source inspection',
                        line=item.line,
                        column=item.column,
                    )
                )

    deduped: dict[tuple[str, str, int | None, int | None], PermissionUse] = {}
    for entry in uses:
        key = (entry.permission, entry.reason, entry.line, entry.column)
        deduped[key] = entry
    return sorted(
        deduped.values(),
        key=lambda entry: (
            entry.permission,
            "" if entry.reason is None else entry.reason,
            -1 if entry.line is None else entry.line,
            -1 if entry.column is None else entry.column,
        ),
    )


def _state_ui_key(target: object) -> str | None:
    if not isinstance(target, ir.StatePath):
        return None
    path = list(getattr(target, "path", []) or [])
    if len(path) < 2:
        return None
    if path[0] != "ui":
        return None
    key = str(path[1] or "")
    return key or None


def _walk_page_items(page: ir.Page) -> list[ir.PageItem]:
    ordered: list[ir.PageItem] = []
    ordered.extend(_walk_items(getattr(page, "items", []) or []))
    layout = getattr(page, "layout", None)
    if layout is not None:
        for slot in ("header", "sidebar_left", "main", "drawer_right", "footer", "diagnostics"):
            ordered.extend(_walk_items(getattr(layout, slot, None) or []))
    return ordered


def _walk_items(items: list[ir.PageItem]) -> list[ir.PageItem]:
    seen: list[ir.PageItem] = []
    for item in items:
        seen.append(item)
        if isinstance(item, ir.TabsItem):
            for tab in list(getattr(item, "tabs", []) or []):
                seen.extend(_walk_items(list(getattr(tab, "children", []) or [])))
            continue
        children = getattr(item, "children", None)
        if isinstance(children, list):
            seen.extend(_walk_items(children))
    return seen


def _walk_dataclass_nodes(value: object) -> list[object]:
    nodes: list[object] = []
    if isinstance(value, dict):
        for key in sorted(value.keys(), key=str):
            nodes.extend(_walk_dataclass_nodes(value[key]))
        return nodes
    if isinstance(value, (list, tuple, set)):
        for item in value:
            nodes.extend(_walk_dataclass_nodes(item))
        return nodes
    nodes.append(value)
    if not is_dataclass(value):
        return nodes
    for field in fields(value):
        if field.name in {"line", "column"}:
            continue
        nodes.extend(_walk_dataclass_nodes(getattr(value, field.name)))
    return nodes


__all__ = [
    "AppPermissionsValidationResult",
    "LEGACY_MODE_WARNING",
    "PERMISSION_DOMAIN_ACTIONS",
    "PERMISSION_KEYS",
    "build_permission_matrix",
    "build_ui_state_scope_map",
    "validate_app_permissions",
]
