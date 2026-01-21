from __future__ import annotations

import json
from pathlib import Path

from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.observability.scrub import scrub_payload
from namel3ss.runtime.artifact_contract import ArtifactContract
from namel3ss.runtime.records.ordering import sort_records
from namel3ss.runtime.records.service import save_record_or_raise
from namel3ss.secrets import collect_secret_values


IMPORT_SUMMARY_PATH = "data/imports/last.json"


def import_payload(
    program,
    store,
    config,
    payload: object,
    *,
    project_root: str | Path | None,
    app_path: str | Path | None,
    identity: dict | None = None,
) -> dict:
    if not isinstance(payload, dict):
        return {"ok": False, "error": "Import payload must be a JSON object."}
    records_payload = payload.get("records")
    if not isinstance(records_payload, list):
        return {"ok": False, "error": "Import payload requires a records list."}
    schemas = {schema.name: schema for schema in getattr(program, "records", [])}
    if identity is None:
        identity = dict(getattr(config, "identity", {}).defaults) if config else {}
    summary_records: list[dict] = []
    errors: list[dict] = []
    for entry in sorted(records_payload, key=lambda item: str(item.get("name") if isinstance(item, dict) else "")):
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        if not name:
            continue
        schema = schemas.get(str(name))
        if schema is None:
            errors.append({"record": str(name), "message": "Record schema not found."})
            continue
        rows = entry.get("rows")
        if not isinstance(rows, list):
            errors.append({"record": str(name), "message": "Record rows must be a list."})
            continue
        valid_rows = [row for row in rows if isinstance(row, dict)]
        ordered_rows = sort_records(schema, valid_rows)
        imported = 0
        for row in ordered_rows:
            try:
                save_record_or_raise(
                    schema.name,
                    dict(row),
                    schemas,
                    {},
                    store,
                    identity=identity,
                )
                imported += 1
            except Namel3ssError as err:
                errors.append({"record": schema.name, "message": str(err)})
        summary_records.append({"name": schema.name, "count": imported})
    summary = {
        "ok": not errors,
        "records": summary_records,
        "errors": errors,
    }
    if project_root:
        write_import_summary(project_root, summary)
    secret_values = collect_secret_values(config)
    scrubbed = scrub_payload(
        summary,
        secret_values=secret_values,
        project_root=project_root,
        app_path=app_path,
    )
    return scrubbed if isinstance(scrubbed, dict) else summary


def write_import_summary(project_root: str | Path, summary: dict) -> Path:
    contract = ArtifactContract(Path(project_root) / ".namel3ss")
    path = contract.prepare_file(IMPORT_SUMMARY_PATH)
    payload = canonical_json_dumps(summary, pretty=True, drop_run_keys=False)
    path.write_text(payload, encoding="utf-8")
    return path


def load_last_import(project_root: str | Path) -> dict | None:
    path = Path(project_root) / ".namel3ss" / IMPORT_SUMMARY_PATH
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


__all__ = ["import_payload", "load_last_import", "write_import_summary"]
