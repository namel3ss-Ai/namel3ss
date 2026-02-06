from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.typecheck import run_type_check


def infer_schema(program: ast.Program) -> dict[str, object]:
    type_report = run_type_check(program)
    flow_types = type_report.get("flow_types")
    flow_type_map = flow_types if isinstance(flow_types, dict) else {}
    route_inputs = _route_input_map(program)
    records = _record_summary(program)
    flows: list[dict[str, object]] = []
    for flow in sorted(program.flows, key=lambda item: item.name):
        inferred_input = route_inputs.get(flow.name, {})
        inferred_output = str(flow_type_map.get(flow.name) or "unknown")
        flows.append(
            {
                "name": flow.name,
                "input": {key: inferred_input[key] for key in sorted(inferred_input.keys())},
                "output": inferred_output,
            }
        )
    return {
        "ok": True,
        "records": records,
        "flows": flows,
        "count": len(flows),
        "issues": list(type_report.get("issues") or []),
    }


def build_schema_migration_plan(program: ast.Program) -> dict[str, object]:
    inferred = infer_schema(program)
    flow_lookup = {
        str(item.get("name")): item
        for item in inferred.get("flows", [])
        if isinstance(item, dict) and item.get("name")
    }
    operations: list[dict[str, object]] = []
    for route in sorted(program.routes, key=lambda item: item.name):
        flow = flow_lookup.get(route.flow_name)
        if not flow:
            continue
        inferred_output = str(flow.get("output") or "unknown")
        if inferred_output == "unknown" or not route.response:
            operations.append(
                {
                    "kind": "annotate_flow_output",
                    "flow": route.flow_name,
                    "route": route.name,
                    "target_type": inferred_output,
                    "reason": "Flow output could not be inferred with confidence.",
                }
            )
            continue
        if len(route.response) != 1:
            continue
        response_field = next(iter(route.response.values()))
        route_type = str(response_field.type_name)
        if route_type != inferred_output:
            operations.append(
                {
                    "kind": "widen_route_response",
                    "route": route.name,
                    "field": response_field.name,
                    "from": route_type,
                    "to": _widen_union(route_type, inferred_output),
                    "reason": "Route response and inferred flow output differ.",
                }
            )
    for record in sorted(program.records, key=lambda item: item.name):
        version = getattr(record, "version", None)
        if not isinstance(version, str) or not version.strip():
            operations.append(
                {
                    "kind": "add_record_version",
                    "record": record.name,
                    "version": "1.0",
                    "reason": "Version metadata is missing.",
                }
            )
    return {
        "ok": True,
        "count": len(operations),
        "operations": operations,
    }


def _route_input_map(program: ast.Program) -> dict[str, dict[str, str]]:
    mapping: dict[str, dict[str, str]] = {}
    for route in sorted(program.routes, key=lambda item: item.name):
        fields = mapping.setdefault(route.flow_name, {})
        for name, field in sorted((route.parameters or {}).items(), key=lambda item: item[0]):
            fields[name] = field.type_name
        for name, field in sorted((route.request or {}).items(), key=lambda item: item[0]):
            fields[name] = field.type_name
    return mapping


def _record_summary(program: ast.Program) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for record in sorted(program.records, key=lambda item: item.name):
        version = getattr(record, "version", None)
        fields = [
            {"name": field.name, "type": field.type_name}
            for field in sorted(record.fields, key=lambda item: item.name)
        ]
        items.append(
            {
                "name": record.name,
                "version": version if isinstance(version, str) and version.strip() else None,
                "fields": fields,
            }
        )
    return items


def _widen_union(left: str, right: str) -> str:
    pieces: list[str] = []
    for raw in [left, right]:
        for part in [item.strip() for item in raw.split("|")]:
            if part and part not in pieces:
                pieces.append(part)
    if len(pieces) == 1:
        return pieces[0]
    return " | ".join(sorted(pieces))


__all__ = ["build_schema_migration_plan", "infer_schema"]
