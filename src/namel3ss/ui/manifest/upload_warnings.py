from __future__ import annotations

from typing import Any

from namel3ss.validation import add_warning


def append_upload_warnings(pages: list[dict], warnings: list | None, context: dict | None = None) -> None:
    del pages  # Upload warnings are declaration-based and use compiler context only.
    if warnings is None:
        return
    ctx = context if isinstance(context, dict) else {}
    capabilities = set(_list_of_strings(ctx.get("capabilities")))
    requests = _list_of_dicts(ctx.get("upload_requests"))
    referenced_names = set(_list_of_strings(ctx.get("upload_reference_names")))

    findings: list[dict[str, Any]] = []
    if "uploads" in capabilities and not requests:
        findings.append(
            {
                "code": "upload.missing_control",
                "message": "Uploads are enabled but no upload control is declared in any page.",
                "fix": "Add `upload <name>` to a page so users can select files.",
                "path": "app.uploads",
                "line": None,
                "column": None,
            }
        )
    for request in requests:
        name = request.get("name")
        if not isinstance(name, str) or not name:
            continue
        if name in referenced_names:
            continue
        findings.append(
            {
                "code": "upload.unused_declaration",
                "message": f"Upload '{name}' is declared but not referenced from state.uploads.{name}.",
                "fix": f"Reference `state.uploads.{name}` in a flow or remove the upload declaration.",
                "path": f"state.uploads.{name}",
                "line": request.get("line"),
                "column": request.get("column"),
            }
        )

    for finding in sorted(findings, key=_sort_key):
        add_warning(
            warnings,
            code=str(finding.get("code") or "upload.warning"),
            message=str(finding.get("message") or "Upload warning."),
            fix=str(finding.get("fix") or ""),
            path=finding.get("path"),
            line=_int_or_none(finding.get("line")),
            column=_int_or_none(finding.get("column")),
            category="upload",
        )


def _sort_key(entry: dict[str, Any]) -> tuple[str, str, int, int, str]:
    return (
        str(entry.get("code") or ""),
        str(entry.get("path") or ""),
        _int_or_none(entry.get("line")) or 0,
        _int_or_none(entry.get("column")) or 0,
        str(entry.get("message") or ""),
    )


def _list_of_strings(value: object) -> list[str]:
    if not isinstance(value, (list, tuple, set)):
        return []
    items: list[str] = []
    for item in value:
        if isinstance(item, str) and item:
            items.append(item)
    return items


def _list_of_dicts(value: object) -> list[dict]:
    if not isinstance(value, (list, tuple)):
        return []
    return [item for item in value if isinstance(item, dict)]


def _int_or_none(value: object) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return None


__all__ = ["append_upload_warnings"]
