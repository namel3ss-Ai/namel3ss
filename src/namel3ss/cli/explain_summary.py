from __future__ import annotations

from namel3ss.persistence.local_store import LocalStore


def summarize_capsules(proof: dict) -> list[dict]:
    capsules = proof.get("capsules", {})
    modules = capsules.get("modules", []) if isinstance(capsules, dict) else []
    summary = []
    for module in modules:
        if not isinstance(module, dict):
            continue
        source = module.get("source", {})
        entry = {
            "name": module.get("name"),
            "source": source.get("kind") if isinstance(source, dict) else None,
        }
        summary.append(entry)
    return summary


def summarize_routes(program) -> list[dict]:
    routes = getattr(program, "routes", []) or []
    summary: list[dict] = []
    for route in routes:
        summary.append(
            {
                "name": route.name,
                "path": route.path,
                "method": route.method,
                "flow": route.flow_name,
                "upload": bool(route.upload) if route.upload else False,
                "generated": bool(getattr(route, "generated", False)),
                "parameters": _summarize_route_fields(getattr(route, "parameters", None)),
                "request": _summarize_route_fields(getattr(route, "request", None)),
                "response": _summarize_route_fields(getattr(route, "response", None)),
            }
        )
    return summary


def summarize_ai_metadata(program) -> list[dict]:
    summary: list[dict] = []
    for flow in getattr(program, "flows", []) or []:
        metadata = getattr(flow, "ai_metadata", None)
        if metadata is None:
            continue
        summary.append(
            {
                "flow": flow.name,
                "model": metadata.model,
                "prompt": metadata.prompt,
                "dataset": metadata.dataset,
                "kind": getattr(metadata, "kind", None),
                "output_type": getattr(metadata, "output_type", None),
                "labels": list(getattr(metadata, "labels", []) or []) or None,
                "sources": list(getattr(metadata, "sources", []) or []) or None,
            }
        )
    return summary


def summarize_crud(program) -> list[dict]:
    summary: list[dict] = []
    for crud in getattr(program, "crud", []) or []:
        summary.append({"record": crud.record_name})
    return summary


def summarize_prompts(program) -> list[dict]:
    summary: list[dict] = []
    for prompt in getattr(program, "prompts", []) or []:
        summary.append(
            {
                "name": prompt.name,
                "version": prompt.version,
                "text": prompt.text,
                "description": prompt.description,
            }
        )
    return summary


def summarize_ai_flows(program) -> list[dict]:
    summary: list[dict] = []
    for flow in getattr(program, "ai_flows", []) or []:
        summary.append(
            {
                "name": flow.name,
                "kind": flow.kind,
                "model": flow.model,
                "prompt": flow.prompt,
                "dataset": flow.dataset,
                "output_type": flow.output_type,
                "labels": list(flow.labels) if flow.labels else None,
                "sources": list(flow.sources) if flow.sources else None,
            }
        )
    return summary


def summarize_datasets(program) -> list[dict]:
    store = LocalStore(getattr(program, "project_root", None), getattr(program, "app_path", None))
    datasets = store.load_datasets()
    return [dict(entry) for entry in datasets if isinstance(entry, dict)]


def _summarize_route_fields(fields: dict | None) -> list[dict] | None:
    if not fields:
        return None
    summary = []
    for name, field in fields.items():
        summary.append({"name": name, "type": getattr(field, "type_name", None)})
    return summary


__all__ = [
    "summarize_ai_flows",
    "summarize_ai_metadata",
    "summarize_capsules",
    "summarize_crud",
    "summarize_datasets",
    "summarize_prompts",
    "summarize_routes",
]
