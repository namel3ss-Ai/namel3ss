from __future__ import annotations

_MAX_REASON_ITEMS = 8


def _join_limited(items: list[str], *, sep: str = ", ") -> str:
    filtered = [str(item) for item in items if item]
    if not filtered:
        return ""
    if len(filtered) <= _MAX_REASON_ITEMS:
        return sep.join(filtered)
    head = filtered[:_MAX_REASON_ITEMS]
    remaining = len(filtered) - _MAX_REASON_ITEMS
    return f"{sep.join(head)}{sep}... (+{remaining} more)"


def _table_reasons(element: dict) -> list[str]:
    reasons: list[str] = []
    columns = element.get("columns") or []
    if columns and element.get("columns_configured"):
        labels = []
        for col in columns:
            name = col.get("name")
            label = col.get("label")
            if label and label != name:
                labels.append(f"{name} ({label})")
            elif name:
                labels.append(str(name))
        if labels:
            joined = _join_limited(labels)
            if joined:
                reasons.append(f"columns: {joined}")
    sort = element.get("sort")
    if isinstance(sort, dict):
        by = sort.get("by")
        order = sort.get("order")
        if by and order:
            reasons.append(f"sort: {by} {order}")
    pagination = element.get("pagination")
    if isinstance(pagination, dict) and pagination.get("page_size") is not None:
        reasons.append(f"pagination: page_size={pagination.get('page_size')}")
    selection = element.get("selection")
    if selection is not None:
        reasons.append(f"selection (ui): {selection}")
    empty_text = element.get("empty_text")
    if empty_text:
        reasons.append(f"empty state: {empty_text}")
    row_actions = element.get("row_actions") or []
    if row_actions:
        labels = [action.get("label") for action in row_actions if action.get("label")]
        joined = _join_limited(labels)
        if joined:
            reasons.append(f"row actions: {joined}")
    return reasons


def _list_reasons(element: dict) -> list[str]:
    reasons: list[str] = []
    variant = element.get("variant")
    if variant:
        reasons.append(f"variant: {variant}")
    mapping = element.get("item")
    if isinstance(mapping, dict):
        parts = []
        for key in ("primary", "secondary", "meta", "icon"):
            value = mapping.get(key)
            if value:
                parts.append(f"{key}={value}")
        joined = _join_limited(parts)
        if joined:
            reasons.append(f"item: {joined}")
    selection = element.get("selection")
    if selection is not None:
        reasons.append(f"selection (ui): {selection}")
    empty_text = element.get("empty_text")
    if empty_text:
        reasons.append(f"empty state: {empty_text}")
    actions = element.get("actions") or []
    if actions:
        labels = [action.get("label") for action in actions if action.get("label")]
        joined = _join_limited(labels)
        if joined:
            reasons.append(f"actions: {joined}")
    return reasons


def _chart_reasons(element: dict) -> list[str]:
    reasons: list[str] = []
    chart_type = element.get("chart_type")
    if chart_type:
        reasons.append(f"type: {chart_type}")
    x = element.get("x")
    y = element.get("y")
    if x or y:
        parts = []
        if x:
            parts.append(f"x={x}")
        if y:
            parts.append(f"y={y}")
        reasons.append(f"mapping: {', '.join(parts)}")
    explain = element.get("explain")
    if explain:
        reasons.append(f"explain: {explain}")
    return reasons


def _tabs_reasons(element: dict) -> list[str]:
    reasons: list[str] = []
    labels = element.get("tabs")
    if isinstance(labels, list) and labels:
        joined = _join_limited([str(label) for label in labels])
        if joined:
            reasons.append(f"tabs: {joined}")
    default_label = element.get("default")
    if default_label:
        reasons.append(f"default: {default_label}")
    active_label = element.get("active")
    if active_label:
        reasons.append(f"active (ui): {active_label}")
    return reasons


def _overlay_reasons(element: dict) -> list[str]:
    reasons: list[str] = []
    open_state = element.get("open")
    if isinstance(open_state, bool):
        reasons.append(f"open (ui): {str(open_state).lower()}")
    open_actions = element.get("open_actions") or []
    if open_actions:
        joined = _join_limited([str(action) for action in open_actions])
        if joined:
            reasons.append(f"open actions (ui): {joined}")
    close_actions = element.get("close_actions") or []
    if close_actions:
        joined = _join_limited([str(action) for action in close_actions])
        if joined:
            reasons.append(f"close actions (ui): {joined}")
    return reasons


def _chat_reasons(element: dict) -> list[str]:
    return []


def _chat_item_reasons(element: dict) -> list[str]:
    reasons: list[str] = []
    kind = element.get("type")
    if kind == "composer":
        flow = element.get("flow")
        if flow:
            reasons.append(f"calls flow: {flow}")
        fields = element.get("fields") or []
        if isinstance(fields, list) and fields:
            names = [field.get("name") for field in fields if isinstance(field, dict) and field.get("name")]
            joined = _join_limited([str(name) for name in names if name])
            if joined:
                reasons.append(f"fields: {joined}")
    if kind == "thinking":
        active = element.get("active")
        if isinstance(active, bool):
            reasons.append(f"active (ui): {str(active).lower()}")
    if kind == "memory":
        lane = element.get("lane")
        if lane:
            reasons.append(f"lane: {lane}")
    return reasons


def _form_reasons(element: dict) -> list[str]:
    reasons: list[str] = []
    groups = element.get("groups")
    if isinstance(groups, list) and groups:
        parts = []
        for group in groups:
            label = group.get("label") or ""
            fields = group.get("fields") or []
            if fields:
                parts.append(f"{label}: {', '.join(str(name) for name in fields)}")
            else:
                parts.append(label)
        joined = _join_limited(parts, sep="; ")
        if joined:
            reasons.append(f"groups: {joined}")
    fields = element.get("fields") or []
    help_fields = [field.get("name") for field in fields if field.get("help")]
    if help_fields:
        joined = _join_limited([str(name) for name in help_fields if name])
        if joined:
            reasons.append(f"help: {joined}")
    readonly_fields = [field.get("name") for field in fields if field.get("readonly")]
    if readonly_fields:
        joined = _join_limited([str(name) for name in readonly_fields if name])
        if joined:
            reasons.append(f"readonly: {joined}")
    constraint_lines = []
    for field in fields:
        constraints = field.get("constraints") or []
        if not constraints:
            continue
        name = field.get("name")
        entries = [_format_constraint(entry) for entry in constraints]
        entries = [entry for entry in entries if entry]
        if name and entries:
            constraint_lines.append(f"{name} ({', '.join(entries)})")
    joined = _join_limited(constraint_lines)
    if joined:
        reasons.append(f"constraints: {joined}")
    return reasons


def _format_constraint(constraint: dict) -> str:
    kind = constraint.get("kind")
    if not kind:
        return ""
    if kind in {"present", "unique", "integer"}:
        return kind
    if kind in {"pattern", "greater_than", "at_least", "less_than", "at_most", "length_min", "length_max"}:
        value = constraint.get("value")
        if value is None:
            return kind
        return f"{kind} {value}"
    if kind == "between":
        return f"between {constraint.get('min')} and {constraint.get('max')}"
    return str(kind)


def _card_reasons(element: dict) -> list[str]:
    reasons: list[str] = []
    stat = element.get("stat")
    if isinstance(stat, dict):
        label = stat.get("label")
        source = stat.get("source")
        if label and source:
            reasons.append(f"stat: {label} = {source}")
        elif source:
            reasons.append(f"stat: {source}")
        elif label:
            reasons.append(f"stat: {label}")
    actions = element.get("actions") or []
    if actions:
        labels = [action.get("label") for action in actions if action.get("label")]
        joined = _join_limited(labels)
        if joined:
            reasons.append(f"actions: {joined}")
    return reasons


def _upload_reasons(element: dict) -> list[str]:
    reasons: list[str] = ["upload contract: progress, preview, state, error"]
    accept = element.get("accept")
    if isinstance(accept, list) and accept:
        joined = _join_limited([str(entry) for entry in accept])
        if joined:
            reasons.append(f"accepts: {joined}")
    multiple = element.get("multiple")
    if isinstance(multiple, bool):
        reasons.append(f"multiple: {str(multiple).lower()}")
    return reasons


__all__ = [
    "_card_reasons",
    "_chart_reasons",
    "_chat_item_reasons",
    "_chat_reasons",
    "_form_reasons",
    "_list_reasons",
    "_overlay_reasons",
    "_table_reasons",
    "_tabs_reasons",
    "_upload_reasons",
]
