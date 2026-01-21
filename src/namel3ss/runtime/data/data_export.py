from __future__ import annotations

import json
from pathlib import Path

from namel3ss.determinism import canonical_json_dumps
from namel3ss.observability.scrub import scrub_payload
from namel3ss.runtime.artifact_contract import ArtifactContract
from namel3ss.runtime.records.inspection import build_records_payload, collect_record_rows
from namel3ss.schema.evolution import build_schema_snapshot
from namel3ss.secrets import collect_secret_values


EXPORT_SUMMARY_PATH = "data/exports/last.json"


def export_payload(
    program,
    store,
    config,
    *,
    project_root: str | Path | None,
    app_path: str | Path | None,
    destination: str | None = None,
    identity: dict | None = None,
) -> dict:
    records = sorted(getattr(program, "records", []), key=lambda rec: rec.name)
    rows, errors = collect_record_rows(records, store, identity)
    records_payload = build_records_payload(records, rows, errors, limit=None)
    payload = {
        "ok": True,
        "schema": build_schema_snapshot(records),
        "records": records_payload,
    }
    if errors:
        payload["errors"] = [{"record": key, "message": value} for key, value in sorted(errors.items())]
    summary = _build_summary(records_payload, destination)
    if project_root:
        write_export_summary(project_root, summary)
    secret_values = collect_secret_values(config)
    scrubbed = scrub_payload(
        payload,
        secret_values=secret_values,
        project_root=project_root,
        app_path=app_path,
    )
    return scrubbed if isinstance(scrubbed, dict) else payload


def write_export_summary(project_root: str | Path, summary: dict) -> Path:
    contract = ArtifactContract(Path(project_root) / ".namel3ss")
    path = contract.prepare_file(EXPORT_SUMMARY_PATH)
    payload = canonical_json_dumps(summary, pretty=True, drop_run_keys=False)
    path.write_text(payload, encoding="utf-8")
    return path


def load_last_export(project_root: str | Path) -> dict | None:
    path = Path(project_root) / ".namel3ss" / EXPORT_SUMMARY_PATH
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _build_summary(records_payload: list[dict], destination: str | None) -> dict:
    summary_records = []
    total = 0
    for entry in records_payload:
        count = entry.get("count") if isinstance(entry, dict) else None
        count_value = int(count) if isinstance(count, int) else 0
        total += count_value
        name = entry.get("name") if isinstance(entry, dict) else None
        if name:
            summary_records.append({"name": str(name), "count": count_value})
    summary = {
        "ok": True,
        "total": total,
        "records": summary_records,
    }
    if destination:
        summary["destination"] = destination
    return summary


__all__ = ["export_payload", "load_last_export", "write_export_summary"]
