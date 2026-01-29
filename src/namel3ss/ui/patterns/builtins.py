from __future__ import annotations

from typing import List

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.ui.patterns.model import PatternDefinition


def builtin_patterns() -> list[PatternDefinition]:
    return [
        _loading_state_pattern(),
        _empty_state_pattern(),
        _error_state_pattern(),
        _results_layout_pattern(),
        _status_banner_pattern(),
    ]


def _loading_state_pattern() -> PatternDefinition:
    params = [
        _param("intent", "text", optional=True, default="spinner"),
        _param("message", "text", optional=True, default="Loading"),
    ]
    return PatternDefinition(
        name="Loading State",
        parameters=params,
        builder=_loading_state_builder,
    )


def _empty_state_pattern() -> PatternDefinition:
    params = [
        _param("heading", "text"),
        _param("guidance", "text"),
        _param("action_label", "text", optional=True),
        _param("action_flow", "text", optional=True),
    ]
    return PatternDefinition(
        name="Empty State",
        parameters=params,
        builder=_empty_state_builder,
    )


def _error_state_pattern() -> PatternDefinition:
    params = [
        _param("heading", "text"),
        _param("message", "text"),
        _param("action_label", "text", optional=True),
        _param("action_flow", "text", optional=True),
    ]
    return PatternDefinition(
        name="Error State",
        parameters=params,
        builder=_error_state_builder,
    )


def _results_layout_pattern() -> PatternDefinition:
    params = [
        _param("record_name", "record"),
        _param("layout", "text", optional=True, default="table"),
        _param("filters_title", "text", optional=True),
        _param("filters_guidance", "text", optional=True),
        _param("empty_title", "text", optional=True),
        _param("empty_guidance", "text", optional=True),
        _param("empty_action_label", "text", optional=True),
        _param("empty_action_flow", "text", optional=True),
    ]
    return PatternDefinition(
        name="Results Layout",
        parameters=params,
        builder=_results_layout_builder,
    )


def _status_banner_pattern() -> PatternDefinition:
    params = [
        _param("tone", "text"),
        _param("heading", "text"),
        _param("message", "text", optional=True),
        _param("action_label", "text", optional=True),
        _param("action_flow", "text", optional=True),
    ]
    return PatternDefinition(
        name="Status Banner",
        parameters=params,
        builder=_status_banner_builder,
    )


def _loading_state_builder(values: dict[str, object], invocation_path: List[int]) -> list[ast.PageItem]:
    intent = _require_text(values, "intent")
    intent_value = intent.lower()
    if intent_value not in {"spinner", "skeleton"}:
        raise Namel3ssError("Loading State intent must be 'spinner' or 'skeleton'")
    message = _require_text(values, "message")
    compose_name = _compose_name("loading", intent_value, invocation_path)
    return [
        ast.ComposeItem(
            name=compose_name,
            children=[ast.TextItem(value=message, visibility=None, line=None, column=None)],
            visibility=None,
            line=None,
            column=None,
        )
    ]


def _empty_state_builder(values: dict[str, object], invocation_path: List[int]) -> list[ast.PageItem]:
    heading = _require_text(values, "heading")
    guidance = _require_text(values, "guidance")
    action_label = _optional_text(values, "action_label")
    action_flow = _optional_text(values, "action_flow")
    if (action_label is None) != (action_flow is None):
        raise Namel3ssError("Empty State action requires both action_label and action_flow")
    children: list[ast.PageItem] = [
        ast.TitleItem(value=heading, visibility=None, line=None, column=None),
        ast.TextItem(value=guidance, visibility=None, line=None, column=None),
    ]
    if action_label is not None and action_flow is not None:
        children.append(
            ast.ButtonItem(label=action_label, flow_name=action_flow, visibility=None, line=None, column=None)
        )
    return [ast.SectionItem(label=None, children=children, visibility=None, line=None, column=None)]


def _error_state_builder(values: dict[str, object], invocation_path: List[int]) -> list[ast.PageItem]:
    heading = _require_text(values, "heading")
    message = _require_text(values, "message")
    action_label = _optional_text(values, "action_label")
    action_flow = _optional_text(values, "action_flow")
    if (action_label is None) != (action_flow is None):
        raise Namel3ssError("Error State action requires both action_label and action_flow")
    children: list[ast.PageItem] = [
        ast.TitleItem(value=heading, visibility=None, line=None, column=None),
        ast.TextItem(value=message, visibility=None, line=None, column=None),
    ]
    if action_label is not None and action_flow is not None:
        children.append(
            ast.ButtonItem(label=action_label, flow_name=action_flow, visibility=None, line=None, column=None)
        )
    return [ast.SectionItem(label=None, children=children, visibility=None, line=None, column=None)]


def _results_layout_builder(values: dict[str, object], invocation_path: List[int]) -> list[ast.PageItem]:
    record_name = _require_text(values, "record_name")
    layout = _require_text(values, "layout").lower()
    if layout not in {"table", "list"}:
        raise Namel3ssError("Results Layout layout must be 'table' or 'list'")
    filters_title = _optional_text(values, "filters_title")
    filters_guidance = _optional_text(values, "filters_guidance")
    if layout == "list":
        items: list[ast.PageItem] = [
            ast.ListItem(
                record_name=record_name,
                variant=None,
                item=None,
                empty_text=None,
                selection=None,
                actions=None,
                visibility=None,
                line=None,
                column=None,
            )
        ]
    else:
        items = [
            ast.TableItem(
                record_name=record_name,
                columns=None,
                empty_text=None,
                sort=None,
                pagination=None,
                selection=None,
                row_actions=None,
                visibility=None,
                line=None,
                column=None,
            )
        ]
    if filters_title is not None or filters_guidance is not None:
        if filters_title is None:
            raise Namel3ssError("Results Layout filters require filters_title")
        filter_children: list[ast.PageItem] = []
        if filters_guidance:
            filter_children.append(ast.TextItem(value=filters_guidance, visibility=None, line=None, column=None))
        items.insert(
            0,
            ast.SectionItem(label=filters_title, children=filter_children, visibility=None, line=None, column=None),
        )
    empty_title = _optional_text(values, "empty_title")
    empty_guidance = _optional_text(values, "empty_guidance")
    empty_action_label = _optional_text(values, "empty_action_label")
    empty_action_flow = _optional_text(values, "empty_action_flow")
    empty_requested = any(
        value is not None
        for value in (empty_title, empty_guidance, empty_action_label, empty_action_flow)
    )
    if empty_requested:
        if empty_title is None or empty_guidance is None:
            raise Namel3ssError("Results Layout empty state requires empty_title and empty_guidance")
        if (empty_action_label is None) != (empty_action_flow is None):
            raise Namel3ssError("Results Layout empty state action requires empty_action_label and empty_action_flow")
        args: list[ast.PatternArgument] = [
            _arg("heading", empty_title),
            _arg("guidance", empty_guidance),
        ]
        if empty_action_label is not None and empty_action_flow is not None:
            args.append(_arg("action_label", empty_action_label))
            args.append(_arg("action_flow", empty_action_flow))
        items.append(
            ast.UsePatternItem(
                pattern_name="Empty State",
                arguments=args,
                visibility=None,
                line=None,
                column=None,
            )
        )
    return items


def _status_banner_builder(values: dict[str, object], invocation_path: List[int]) -> list[ast.PageItem]:
    tone = _require_text(values, "tone").lower()
    if tone not in {"success", "caution", "critical"}:
        raise Namel3ssError("Status Banner tone must be 'success', 'caution', or 'critical'")
    heading = _require_text(values, "heading")
    message = _optional_text(values, "message")
    action_label = _optional_text(values, "action_label")
    action_flow = _optional_text(values, "action_flow")
    if (action_label is None) != (action_flow is None):
        raise Namel3ssError("Status Banner action requires both action_label and action_flow")
    children: list[ast.PageItem] = [
        ast.TitleItem(value=heading, visibility=None, line=None, column=None),
    ]
    if message is not None:
        children.append(ast.TextItem(value=message, visibility=None, line=None, column=None))
    if action_label is not None and action_flow is not None:
        children.append(
            ast.ButtonItem(label=action_label, flow_name=action_flow, visibility=None, line=None, column=None)
        )
    return [ast.SectionItem(label=_status_label(tone), children=children, visibility=None, line=None, column=None)]


def _compose_name(prefix: str, intent: str, invocation_path: List[int]) -> str:
    suffix = "_".join(str(entry) for entry in invocation_path) if invocation_path else "root"
    safe_intent = _sanitize_identifier(intent)
    return f"{prefix}_{safe_intent}_{suffix}"


def _sanitize_identifier(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() else "_" for ch in value.lower())
    cleaned = cleaned.strip("_")
    return cleaned or "item"


def _param(name: str, kind: str, *, optional: bool = False, default: object | None = None) -> ast.PatternParam:
    return ast.PatternParam(
        name=name,
        kind=kind,
        optional=optional,
        default=default,
        line=None,
        column=None,
    )


def _arg(name: str, value: object) -> ast.PatternArgument:
    return ast.PatternArgument(name=name, value=value, line=None, column=None)


def _require_text(values: dict[str, object], name: str) -> str:
    value = values.get(name)
    if not isinstance(value, str):
        raise Namel3ssError(f"{name} must be text")
    return value


def _optional_text(values: dict[str, object], name: str) -> str | None:
    value = values.get(name)
    if value is None:
        return None
    if not isinstance(value, str):
        raise Namel3ssError(f"{name} must be text")
    return value

def _status_label(tone: str) -> str:
    labels = {"success": "Success", "caution": "Caution", "critical": "Critical"}
    return labels.get(tone, tone.title())


__all__ = ["builtin_patterns"]
