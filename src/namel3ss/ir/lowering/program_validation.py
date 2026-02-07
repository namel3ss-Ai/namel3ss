from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ir.lowering.expressions import _lower_expression
from namel3ss.ir.model.contracts import ContractDecl
from namel3ss.ir.model.expressions import Literal as IRLiteral
from namel3ss.ir.model.expressions import StatePath as IRStatePath
from namel3ss.ir.model.flow_steps import FlowInput
from namel3ss.ir.model.pages import (
    ActivePageRule,
    CardGroupItem,
    CardItem,
    ChatComposerItem,
    ChatItem,
    ColumnItem,
    ComposeItem,
    DrawerItem,
    GridItem,
    ModalItem,
    Page,
    RowItem,
    SectionItem,
    TabsItem,
    TextInputItem,
)
from namel3ss.ir.model.program import Flow
from namel3ss.ir.model.responsive import ResponsiveLayout
from namel3ss.lang.capabilities import normalize_builtin_capability
from namel3ss.utils.numbers import is_number, to_decimal


def _ensure_unique_pages(pages: list[Page]) -> None:
    seen: dict[str, object] = {}
    for page in pages:
        if page.name in seen:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Page '{page.name}' is declared more than once.",
                    why="Pages must have unique names.",
                    fix="Rename the duplicate page or merge its contents.",
                    example='page "home":',
                ),
                line=getattr(page, "line", None),
                column=getattr(page, "column", None),
            )
        seen[page.name] = True


def _validate_responsive_theme_scales(
    *,
    responsive_tokens: dict[str, tuple[int, ...]],
    responsive_layout: ResponsiveLayout | None,
    line: int | None,
    column: int | None,
) -> None:
    if not responsive_tokens:
        return
    if responsive_layout is None:
        return
    breakpoint_count = 0
    if responsive_layout is not None:
        breakpoint_count = len(tuple(getattr(getattr(responsive_layout, "breakpoints", None), "names", ()) or ()))
    expected_length = breakpoint_count + 1
    for token_name in sorted(responsive_tokens.keys()):
        values = tuple(responsive_tokens.get(token_name, ()))
        if len(values) != expected_length:
            raise Namel3ssError(
                (
                    f"Responsive token '{token_name}' defines {len(values)} values, "
                    f"but expected {expected_length} (default + {breakpoint_count} breakpoints)."
                ),
                line=line,
                column=column,
            )


def _lower_active_page_rules(
    rules: list[ast.ActivePageRule] | None,
    page_names: set[str],
) -> list[ActivePageRule] | None:
    if not rules:
        return None
    lowered: list[ActivePageRule] = []
    seen: dict[tuple[tuple[str, ...], object], str] = {}
    for rule in rules:
        if not isinstance(rule, ast.ActivePageRule):
            raise Namel3ssError(
                "Active page rules require: is \"<page>\" only when state.<path> is <value>.",
                line=getattr(rule, "line", None),
                column=getattr(rule, "column", None),
            )
        if rule.page_name not in page_names:
            raise Namel3ssError(
                f"Active page rule references unknown page '{rule.page_name}'.",
                line=getattr(rule, "line", None),
                column=getattr(rule, "column", None),
            )
        lowered_path = _lower_expression(rule.path)
        if not isinstance(lowered_path, IRStatePath):
            raise Namel3ssError(
                "Active page rules require state.<path>.",
                line=getattr(rule, "line", None),
                column=getattr(rule, "column", None),
            )
        lowered_value = _lower_expression(rule.value)
        if not isinstance(lowered_value, IRLiteral):
            raise Namel3ssError(
                "Active page rules require a text, number, or boolean literal.",
                line=getattr(rule, "line", None),
                column=getattr(rule, "column", None),
            )
        key = _active_page_rule_key(lowered_path.path, lowered_value.value)
        if key in seen:
            raise Namel3ssError(
                "Active page rules must be unique for each state value.",
                line=getattr(rule, "line", None),
                column=getattr(rule, "column", None),
            )
        seen[key] = rule.page_name
        lowered.append(
            ActivePageRule(
                page_name=rule.page_name,
                path=lowered_path,
                value=lowered_value,
                line=rule.line,
                column=rule.column,
            )
        )
    return lowered


def _active_page_rule_key(path: list[str], value: object) -> tuple[tuple[str, ...], object]:
    if is_number(value):
        return (tuple(path), to_decimal(value))
    return (tuple(path), value)


def _validate_text_inputs(
    pages: list[Page],
    flows: list[Flow],
    flow_contracts: dict[str, ContractDecl],
) -> None:
    flow_inputs: dict[str, dict[str, str]] = {flow.name: _flow_input_signature(flow, flow_contracts) for flow in flows}
    for page in pages:
        for item in _walk_page_items(page.items):
            if not isinstance(item, TextInputItem):
                continue
            inputs = flow_inputs.get(item.flow_name) or {}
            if not inputs:
                raise Namel3ssError(
                    build_guidance_message(
                        what=f'Text input "{item.name}" targets flow "{item.flow_name}" without input fields.',
                        why="Text inputs require a flow input field with a text type.",
                        fix=f'Add an input block with `{item.name} is text` to the flow.',
                        example=f'flow "{item.flow_name}"\n  input\n    {item.name} is text',
                    ),
                    line=item.line,
                    column=item.column,
                )
            field_type = inputs.get(item.name)
            if field_type is None:
                raise Namel3ssError(
                    build_guidance_message(
                        what=f'Text input "{item.name}" is not declared on flow "{item.flow_name}".',
                        why="The input name must match a flow input field.",
                        fix=f'Add `{item.name} is text` to the flow input block.',
                        example=f'flow "{item.flow_name}"\n  input\n    {item.name} is text',
                    ),
                    line=item.line,
                    column=item.column,
                )
            if field_type != "text":
                raise Namel3ssError(
                    build_guidance_message(
                        what=f'Text input "{item.name}" must bind to a text field.',
                        why=f'Flow "{item.flow_name}" declares "{item.name}" as {field_type}.',
                        fix=f'Change the flow input type to text for "{item.name}".',
                        example=f'flow "{item.flow_name}"\n  input\n    {item.name} is text',
                    ),
                    line=item.line,
                    column=item.column,
                )


def _validate_chat_composers(
    pages: list[Page],
    flows: list[Flow],
    flow_contracts: dict[str, ContractDecl],
) -> None:
    flow_inputs: dict[str, dict[str, str]] = {flow.name: _flow_input_signature(flow, flow_contracts) for flow in flows}
    for page in pages:
        for item in _walk_page_items(page.items):
            if not isinstance(item, ChatComposerItem):
                continue
            inputs = flow_inputs.get(item.flow_name) or {}
            extra_fields = list(getattr(item, "fields", []) or [])
            if not extra_fields:
                if not inputs:
                    continue
                message_type = inputs.get("message")
                if message_type is None:
                    raise Namel3ssError(
                        build_guidance_message(
                            what=f'Chat composer for flow "{item.flow_name}" is missing "message" in inputs.',
                            why="Composer submissions always include message.",
                            fix='Add `message is text` to the flow input block.',
                            example=_composer_input_example(item.flow_name, ["message"]),
                        ),
                        line=item.line,
                        column=item.column,
                    )
                if message_type != "text":
                    raise Namel3ssError(
                        build_guidance_message(
                            what='Chat composer field "message" must be text.',
                            why=f'Flow "{item.flow_name}" declares "message" as {message_type}.',
                            fix='Change the flow input type to text for "message".',
                            example=f'flow "{item.flow_name}"\n  input\n    message is text',
                        ),
                        line=item.line,
                        column=item.column,
                    )
                continue
            expected_fields = _composer_expected_fields(extra_fields)
            if not inputs:
                example = _composer_input_example(item.flow_name, expected_fields)
                raise Namel3ssError(
                    build_guidance_message(
                        what=f'Chat composer for flow "{item.flow_name}" declares extra fields without flow inputs.',
                        why="Structured composers require explicit input fields for validation.",
                        fix="Add an input block that lists message and the extra fields.",
                        example=example,
                    ),
                    line=item.line,
                    column=item.column,
                )
            missing = [name for name in expected_fields if name not in inputs]
            extra = [name for name in inputs.keys() if name not in expected_fields]
            if missing or extra:
                why_parts: list[str] = []
                if missing:
                    why_parts.append(f"Missing: {', '.join(missing)}.")
                if extra:
                    why_parts.append(f"Extra: {', '.join(extra)}.")
                example = _composer_input_example(item.flow_name, expected_fields)
                raise Namel3ssError(
                    build_guidance_message(
                        what=f'Chat composer fields do not match flow "{item.flow_name}" inputs.',
                        why=" ".join(why_parts) if why_parts else "Flow inputs must match composer fields.",
                        fix="Update the flow input block to match the composer payload.",
                        example=example,
                    ),
                    line=item.line,
                    column=item.column,
                )
            type_map = {"message": "text"}
            for field in extra_fields:
                type_map[field.name] = field.type_name
            for name in expected_fields:
                expected_type = type_map.get(name)
                actual_type = inputs.get(name)
                if expected_type and actual_type and actual_type != expected_type:
                    field = next((entry for entry in extra_fields if entry.name == name), None)
                    raise Namel3ssError(
                        build_guidance_message(
                            what=f'Chat composer field "{name}" must be {expected_type}.',
                            why=f'Flow "{item.flow_name}" declares "{name}" as {actual_type}.',
                            fix=f'Change the flow input type to {expected_type} for "{name}".',
                            example=f'flow "{item.flow_name}"\n  input\n    {name} is {expected_type}',
                        ),
                        line=field.line if field else item.line,
                        column=field.column if field else item.column,
                    )


def _validate_page_style_hook_tokens(pages: list[Page], token_registry: dict[str, str]) -> None:
    for page in pages:
        for item in _walk_page_items(page.items):
            style_hooks = getattr(item, "style_hooks", None) or {}
            for hook_name, token_name in style_hooks.items():
                if token_name in token_registry:
                    continue
                raise Namel3ssError(
                    f'Style hook "{hook_name}" references unknown token "{token_name}".',
                    line=getattr(item, "line", None),
                    column=getattr(item, "column", None),
                )


def _flow_input_signature(flow: Flow, flow_contracts: dict[str, ContractDecl]) -> dict[str, str]:
    if flow.steps:
        for step in flow.steps:
            if isinstance(step, FlowInput):
                return {field.name: field.type_name for field in step.fields}
    contract = flow_contracts.get(flow.name)
    if contract is None:
        return {}
    return {field.name: field.type_name for field in contract.signature.inputs}


def _composer_expected_fields(extra_fields: list[object]) -> list[str]:
    names = ["message"]
    for field in extra_fields:
        name = getattr(field, "name", None)
        if isinstance(name, str):
            names.append(name)
    return names


def _composer_input_example(flow_name: str, field_names: list[str]) -> str:
    lines = [f'flow "{flow_name}"', "  input"]
    for name in field_names:
        lines.append(f"    {name} is text")
    return "\n".join(lines)


def _walk_page_items(items: list[object]) -> list[object]:
    collected: list[object] = []
    for item in items:
        collected.append(item)
        if isinstance(
            item,
            (
                SectionItem,
                CardGroupItem,
                CardItem,
                RowItem,
                ColumnItem,
                ComposeItem,
                DrawerItem,
                ModalItem,
                ChatItem,
                GridItem,
            ),
        ):
            collected.extend(_walk_page_items(getattr(item, "children", [])))
            continue
        if isinstance(item, TabsItem):
            for tab in item.tabs:
                collected.extend(_walk_page_items(tab.children))
            continue
    return collected


def _normalize_capabilities(items: list[str]) -> tuple[str, ...]:
    normalized: list[str] = []
    for item in items:
        value = normalize_builtin_capability(item)
        if value:
            normalized.append(value)
    return tuple(sorted(set(normalized)))


def _normalize_pack_allowlist(items: list[str] | None) -> tuple[str, ...] | None:
    if items is None:
        return None
    normalized: list[str] = []
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, str):
            continue
        value = item.strip()
        if not value or value in seen:
            continue
        seen.add(value)
        normalized.append(value)
    if not normalized:
        return None
    return tuple(normalized)


__all__ = [
    "_ensure_unique_pages",
    "_lower_active_page_rules",
    "_normalize_capabilities",
    "_normalize_pack_allowlist",
    "_validate_chat_composers",
    "_validate_page_style_hook_tokens",
    "_validate_responsive_theme_scales",
    "_validate_text_inputs",
]
