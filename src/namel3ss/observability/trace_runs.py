from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from namel3ss.determinism import canonical_json_dump, canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.observability.config import load_observability_config
from namel3ss.observability.scrub import scrub_payload
from namel3ss.runtime.persistence_paths import resolve_persistence_root


TRACE_RUNS_DIRNAME = "traces"
TRACE_INDEX_FILENAME = "index.json"
TRACE_SCHEMA_VERSION = 1


def trace_runs_root(
    project_root: str | Path | None,
    app_path: str | Path | None,
    *,
    allow_create: bool = True,
) -> Path | None:
    root = resolve_persistence_root(project_root, app_path, allow_create=allow_create)
    if root is None:
        return None
    return Path(root) / ".namel3ss" / TRACE_RUNS_DIRNAME


def list_trace_runs(project_root: str | Path | None, app_path: str | Path | None) -> list[dict[str, object]]:
    root = trace_runs_root(project_root, app_path, allow_create=False)
    if root is None:
        return []
    index = _load_trace_index(root)
    runs = index.get("runs")
    if not isinstance(runs, list):
        return []
    normalized: list[dict[str, object]] = []
    for item in runs:
        if not isinstance(item, dict):
            continue
        run_id = str(item.get("run_id", "") or "").strip()
        if not run_id:
            continue
        normalized.append(
            {
                "run_id": run_id,
                "flow_name": str(item.get("flow_name", "") or ""),
                "step_count": _to_int(item.get("step_count"), 0),
                "error_count": _to_int(item.get("error_count"), 0),
                "sequence": _to_int(item.get("sequence"), 0),
            }
        )
    normalized.sort(key=lambda entry: (_to_int(entry.get("sequence"), 0), str(entry.get("run_id", ""))), reverse=True)
    return normalized


def latest_trace_run_id(project_root: str | Path | None, app_path: str | Path | None) -> str | None:
    root = trace_runs_root(project_root, app_path, allow_create=False)
    if root is None:
        return None
    index = _load_trace_index(root)
    latest = index.get("latest_run_id")
    if isinstance(latest, str) and latest.strip():
        return latest.strip()
    runs = list_trace_runs(project_root, app_path)
    if not runs:
        return None
    return str(runs[0].get("run_id", "") or "").strip() or None


def read_trace_entries(
    project_root: str | Path | None,
    app_path: str | Path | None,
    run_id: str,
) -> list[dict[str, object]]:
    root = trace_runs_root(project_root, app_path, allow_create=False)
    if root is None:
        return []
    path = _trace_run_path(root, run_id)
    if not path.exists():
        return []
    entries: list[dict[str, object]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as err:
            raise Namel3ssError(_invalid_trace_file_message(path, err.msg)) from err
        if not isinstance(payload, dict):
            raise Namel3ssError(_invalid_trace_file_message(path, "line entry must be an object"))
        entries.append(payload)
    entries.sort(key=lambda entry: (_to_int(entry.get("timestamp"), 0), str(entry.get("step_id", ""))))
    return entries


def write_trace_run(
    *,
    project_root: str | Path | None,
    app_path: str | Path | None,
    flow_name: str,
    steps: Iterable[dict[str, object]],
    secret_values: Iterable[str] | None = None,
) -> dict[str, object] | None:
    root = trace_runs_root(project_root, app_path, allow_create=True)
    if root is None:
        return None
    root.mkdir(parents=True, exist_ok=True)
    index = _load_trace_index(root)
    sequence = _to_int(index.get("next_counter"), 1)
    if sequence <= 0:
        sequence = 1
    run_id = _build_run_id(flow_name, sequence)
    path = _trace_run_path(root, run_id)

    config = load_observability_config(project_root, app_path)
    redaction_rules = config.redaction_rules
    max_trace_size = config.max_trace_size
    merged_secrets = list(secret_values or [])

    entries = _build_trace_entries(
        flow_name=flow_name,
        steps=list(steps),
        project_root=project_root,
        app_path=app_path,
        secret_values=merged_secrets,
        redaction_rules=redaction_rules,
        max_trace_size=max_trace_size,
    )

    lines = [canonical_json_dumps(item, pretty=False, drop_run_keys=False) for item in entries]
    path.write_text("\n".join(lines).rstrip() + ("\n" if lines else ""), encoding="utf-8")

    summary = {
        "run_id": run_id,
        "flow_name": flow_name,
        "step_count": len(entries),
        "error_count": _count_errors(entries),
        "sequence": sequence,
    }
    runs = index.get("runs")
    next_runs = [item for item in runs if isinstance(item, dict)] if isinstance(runs, list) else []
    next_runs.append(summary)
    next_runs.sort(key=lambda item: (_to_int(item.get("sequence"), 0), str(item.get("run_id", ""))))
    next_index = {
        "schema_version": TRACE_SCHEMA_VERSION,
        "next_counter": sequence + 1,
        "latest_run_id": run_id,
        "runs": next_runs,
    }
    canonical_json_dump(root / TRACE_INDEX_FILENAME, next_index, pretty=True, drop_run_keys=False)
    return summary


def _build_trace_entries(
    *,
    flow_name: str,
    steps: list[dict[str, object]],
    project_root: str | Path | None,
    app_path: str | Path | None,
    secret_values: list[str],
    redaction_rules: dict[str, str],
    max_trace_size: int,
) -> list[dict[str, object]]:
    limited_steps = steps[: max_trace_size]
    entries: list[dict[str, object]] = []
    for index, step in enumerate(limited_steps, start=1):
        data = step.get("data")
        details = data if isinstance(data, dict) else {}
        input_value = details.get("input", details.get("inputs", {}))
        output_value = details.get("output", details.get("result", details.get("value", {})))

        cleaned_input = _apply_redaction(
            input_value,
            project_root=project_root,
            app_path=app_path,
            secret_values=secret_values,
            redaction_rules=redaction_rules,
        )
        cleaned_output = _apply_redaction(
            output_value,
            project_root=project_root,
            app_path=app_path,
            secret_values=secret_values,
            redaction_rules=redaction_rules,
        )
        memory_used = _to_int(
            details.get(
                "memory_used",
                len(canonical_json_dumps(details, pretty=False, drop_run_keys=False)),
            ),
            0,
        )
        entry = {
            "step_id": str(step.get("id") or f"{flow_name}:step:{index:04d}"),
            "timestamp": index,
            "input": cleaned_input if cleaned_input is not None else {},
            "output": cleaned_output if cleaned_output is not None else {},
            "duration_ms": _to_number(details.get("duration_ms"), 0.0),
            "memory_used": memory_used,
            "flow_name": flow_name,
            "step_name": str(step.get("kind") or step.get("what") or f"step_{index}"),
        }
        if step.get("line") is not None:
            entry["line"] = _to_int(step.get("line"), 0)
        if step.get("column") is not None:
            entry["column"] = _to_int(step.get("column"), 0)
        entries.append(entry)
    return entries


def _apply_redaction(
    value: object,
    *,
    project_root: str | Path | None,
    app_path: str | Path | None,
    secret_values: list[str],
    redaction_rules: dict[str, str],
) -> object:
    scrubbed = scrub_payload(
        value,
        secret_values=secret_values,
        project_root=project_root,
        app_path=app_path,
    )
    if not redaction_rules:
        return scrubbed
    return _apply_path_redaction(scrubbed, redaction_rules, path=())


def _apply_path_redaction(value: object, redaction_rules: dict[str, str], *, path: tuple[str, ...]) -> object:
    key = ".".join(path)
    if key in redaction_rules and key:
        return redaction_rules[key]
    if isinstance(value, dict):
        result: dict[str, object] = {}
        for raw_key in sorted(value.keys(), key=lambda item: str(item)):
            child_key = str(raw_key)
            result[child_key] = _apply_path_redaction(value[raw_key], redaction_rules, path=(*path, child_key))
        return result
    if isinstance(value, list):
        return [_apply_path_redaction(item, redaction_rules, path=path) for item in value]
    return value


def _count_errors(entries: list[dict[str, object]]) -> int:
    return sum(1 for entry in entries if str(entry.get("step_name", "")) == "error")


def _build_run_id(flow_name: str, sequence: int) -> str:
    slug = "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in flow_name.strip().lower())
    slug = slug or "flow"
    return f"{slug}-{sequence:06d}"


def _trace_run_path(root: Path, run_id: str) -> Path:
    return root / f"{run_id}.jsonl"


def _load_trace_index(root: Path) -> dict[str, object]:
    path = root / TRACE_INDEX_FILENAME
    if not path.exists():
        return {"schema_version": TRACE_SCHEMA_VERSION, "next_counter": 1, "latest_run_id": None, "runs": []}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"schema_version": TRACE_SCHEMA_VERSION, "next_counter": 1, "latest_run_id": None, "runs": []}
    if not isinstance(payload, dict):
        return {"schema_version": TRACE_SCHEMA_VERSION, "next_counter": 1, "latest_run_id": None, "runs": []}
    payload.setdefault("schema_version", TRACE_SCHEMA_VERSION)
    payload.setdefault("next_counter", 1)
    payload.setdefault("latest_run_id", None)
    payload.setdefault("runs", [])
    return payload


def _to_int(value: object, default: int) -> int:
    if isinstance(value, bool):
        return default
    try:
        return int(value)
    except Exception:
        return default


def _to_number(value: object, default: float) -> float:
    if isinstance(value, bool):
        return default
    try:
        return float(value)
    except Exception:
        return default


def _invalid_trace_file_message(path: Path, details: str) -> str:
    return build_guidance_message(
        what="Trace file is invalid.",
        why=f"{path.as_posix()} could not be parsed: {details}.",
        fix="Delete the corrupted trace file and rerun the flow.",
        example='{"step_id":"flow:step:0001","timestamp":1,"flow_name":"demo","step_name":"flow_start"}',
    )


__all__ = [
    "TRACE_INDEX_FILENAME",
    "TRACE_RUNS_DIRNAME",
    "TRACE_SCHEMA_VERSION",
    "latest_trace_run_id",
    "list_trace_runs",
    "read_trace_entries",
    "trace_runs_root",
    "write_trace_run",
]
