from __future__ import annotations

from namel3ss.determinism import canonical_json_dumps
from namel3ss.docs.sdk_shared import _collect_operations


def generate_postman_collection(spec: dict) -> dict:
    operations = _collect_operations(spec)
    title = (spec.get("info") or {}).get("title") or "namel3ss api"
    items = []
    for op in operations:
        raw_url = "{{base_url}}" + op.path
        query = [{"key": param.name, "value": ""} for param in op.query_params]
        item = {
            "name": op.name,
            "request": {
                "method": op.method.upper(),
                "header": [{"key": "Content-Type", "value": "application/json"}],
                "url": {
                    "raw": raw_url,
                    "host": ["{{base_url}}"],
                    "path": [segment for segment in op.path.strip("/").split("/") if segment],
                    "query": query,
                },
            },
        }
        if op.request_schema and op.method.upper() not in {"GET", "HEAD"}:
            item["request"]["body"] = {"mode": "raw", "raw": "{}"}
        items.append(item)
    return {
        "info": {
            "name": title,
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "item": items,
    }


def render_postman_collection(spec: dict) -> str:
    return canonical_json_dumps(generate_postman_collection(spec), pretty=True, drop_run_keys=False)


__all__ = ["generate_postman_collection", "render_postman_collection"]
