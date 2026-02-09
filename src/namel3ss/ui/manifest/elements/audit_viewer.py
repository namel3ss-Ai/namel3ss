from __future__ import annotations

from typing import Any

from namel3ss.ui.manifest.canonical import _element_id


def inject_audit_viewer_elements(
    manifest: dict,
    *,
    run_artifact: object,
    audit_bundle: object,
    audit_policy_status: object,
) -> dict:
    if not isinstance(manifest, dict):
        return manifest
    pages = manifest.get("pages")
    if not isinstance(pages, list):
        return manifest
    artifact = _sanitize(run_artifact) if isinstance(run_artifact, dict) else {}
    if not artifact:
        return manifest
    bundle = _sanitize(audit_bundle) if isinstance(audit_bundle, dict) else {}
    policy = _sanitize(audit_policy_status) if isinstance(audit_policy_status, dict) else {}
    for page in pages:
        if not isinstance(page, dict):
            continue
        page_slug = str(page.get("slug") or page.get("name") or "page")
        page_name = str(page.get("name") or page_slug)
        element = _audit_viewer_element(
            page_name=page_name,
            page_slug=page_slug,
            run_artifact=artifact,
            audit_bundle=bundle,
            audit_policy_status=policy,
        )
        if isinstance(page.get("layout"), dict):
            layout = page["layout"]
            main_items = layout.get("main")
            if not isinstance(main_items, list):
                main_items = []
            layout["main"] = _inject_element(main_items, element)
            continue
        elements = page.get("elements")
        if not isinstance(elements, list):
            elements = []
            page["elements"] = elements
        page["elements"] = _inject_element(elements, element)
    manifest["run_artifact"] = artifact
    if bundle:
        manifest["audit_bundle"] = bundle
    if policy:
        manifest["audit_policy_status"] = policy
    return manifest


def _inject_element(items: list[dict], element: dict[str, Any]) -> list[dict]:
    filtered = [entry for entry in items if not _is_audit_viewer(entry)]
    if filtered and isinstance(filtered[0], dict) and filtered[0].get("type") == "runtime_error":
        return [filtered[0], element, *filtered[1:]]
    if len(filtered) > 1 and isinstance(filtered[1], dict) and filtered[1].get("type") == "retrieval_explain":
        return [filtered[0], filtered[1], element, *filtered[2:]]
    return [element, *filtered]


def _audit_viewer_element(
    *,
    page_name: str,
    page_slug: str,
    run_artifact: dict[str, Any],
    audit_bundle: dict[str, Any],
    audit_policy_status: dict[str, Any],
) -> dict[str, Any]:
    retrieval_trace = run_artifact.get("retrieval_trace")
    runtime_errors = run_artifact.get("runtime_errors")
    retrieval_count = len(retrieval_trace) if isinstance(retrieval_trace, list) else 0
    runtime_error_count = len(runtime_errors) if isinstance(runtime_errors, list) else 0
    return {
        "type": "audit_viewer",
        "element_id": _element_id(page_slug, "audit_viewer", [0]),
        "page": page_name,
        "page_slug": page_slug,
        "index": 0,
        "line": 0,
        "column": 0,
        "source": "runtime.audit",
        "run_id": str(run_artifact.get("run_id") or ""),
        "schema_version": str(run_artifact.get("schema_version") or ""),
        "retrieval_count": retrieval_count,
        "runtime_error_count": runtime_error_count,
        "checksums": _sanitize(run_artifact.get("checksums")) if isinstance(run_artifact.get("checksums"), dict) else {},
        "audit_bundle": audit_bundle,
        "audit_policy_status": audit_policy_status,
        "run_artifact": run_artifact,
    }


def _is_audit_viewer(entry: object) -> bool:
    return isinstance(entry, dict) and entry.get("type") == "audit_viewer"


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(value[key]) for key in sorted(value.keys(), key=str)}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float, str)) or value is None:
        return value
    return str(value)


__all__ = ["inject_audit_viewer_elements"]
