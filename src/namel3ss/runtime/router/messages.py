from __future__ import annotations

from pathlib import Path

from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.persistence_paths import resolve_persistence_root
from namel3ss.runtime.router.registry import RouteEntry


def format_not_allowed_message(route_name: str, requested: str) -> str:
    return (
        f'Format "{requested}" is not available for route "{route_name}".\n'
        "Why: The route only supports configured formats.\n"
        "Fix: Request a supported format or update formats.yaml.\n"
        "Example: format=json"
    )


def filter_not_allowed_message(route_name: str) -> str:
    return (
        f'Filters are not enabled for route "{route_name}".\n'
        "Why: No filter fields are configured.\n"
        "Fix: Add filter_fields in conventions.yaml or remove the filter parameter.\n"
        "Example: filter=status:open"
    )


def requested_version(query: dict[str, str], headers: dict[str, str]) -> str | None:
    query_value = str(query.get("version") or "").strip()
    if query_value:
        return query_value
    header_value = str(headers.get("Accept-Version") or headers.get("accept-version") or "").strip()
    return header_value or None


def deprecated_headers(entry: RouteEntry) -> dict[str, str] | None:
    if entry.status != "deprecated":
        return None
    return {"X-N3-Deprecation-Warning": deprecation_warning(entry)}


def deprecation_warning(entry: RouteEntry) -> str:
    message = f'route "{entry.entity_name}" version "{entry.version or "default"}" is deprecated'
    if entry.replacement:
        message += f'; use "{entry.replacement}"'
    if entry.deprecation_date:
        message += f"; end_of_life={entry.deprecation_date}"
    return message


def removed_version_message(entry: RouteEntry, requested_version: str) -> str:
    if entry.replacement:
        return (
            f'Route "{entry.entity_name}" version "{requested_version}" was removed. '
            f'Use version "{entry.replacement}" instead.'
        )
    return f'Route "{entry.entity_name}" version "{requested_version}" was removed.'


def log_deprecated_route_call(program, entry: RouteEntry, *, requested_version: str | None) -> None:
    root = resolve_persistence_root(getattr(program, "project_root", None), getattr(program, "app_path", None))
    if root is None:
        return
    log_path = Path(root) / ".namel3ss" / "deprecations.jsonl"
    row = {
        "route_name": entry.name,
        "entity_name": entry.entity_name,
        "version": entry.version or "default",
        "status": entry.status,
        "replacement": entry.replacement or "",
        "deprecation_date": entry.deprecation_date or "",
        "requested_version": requested_version or "",
    }
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(canonical_json_dumps(row, pretty=False, drop_run_keys=False) + "\n")


def status_from_error(err: Namel3ssError) -> int:
    details = err.details if isinstance(err.details, dict) else {}
    status = details.get("http_status")
    if isinstance(status, int):
        return status
    if isinstance(status, str) and status.isdigit():
        return int(status)
    category = details.get("category")
    if category == "authentication":
        return 401
    if category == "permission":
        return 403
    return 400


def error_reason_code(err: Namel3ssError) -> str:
    details = err.details if isinstance(err.details, dict) else {}
    reason = details.get("reason_code")
    if isinstance(reason, str) and reason.strip():
        return reason.strip()
    category = details.get("category")
    if isinstance(category, str) and category.strip():
        return category.strip()
    return "request_error"


__all__ = [
    "deprecated_headers",
    "deprecation_warning",
    "error_reason_code",
    "filter_not_allowed_message",
    "format_not_allowed_message",
    "log_deprecated_route_call",
    "removed_version_message",
    "requested_version",
    "status_from_error",
]
