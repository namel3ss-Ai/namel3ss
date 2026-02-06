from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.explainability.logger import explain_replay_hash, load_explain_log
from namel3ss.utils.json_tools import dumps_pretty


@dataclass(frozen=True)
class _ReplayParams:
    app_arg: str | None
    log_path: Path | None
    json_mode: bool
    strict_hash: bool


def run_replay_command(args: list[str]) -> int:
    params = _parse_args(args)
    log_path = _resolve_log_path(params)
    payload = _build_replay_payload(log_path, strict_hash=params.strict_hash)
    if params.json_mode:
        print(dumps_pretty(payload))
    else:
        _print_human(payload)
    return 0


def _parse_args(args: list[str]) -> _ReplayParams:
    app_arg: str | None = None
    log_path: Path | None = None
    json_mode = False
    strict_hash = True
    index = 0
    while index < len(args):
        token = args[index]
        if token == "--json":
            json_mode = True
            index += 1
            continue
        if token == "--no-verify":
            strict_hash = False
            index += 1
            continue
        if token == "--log":
            if index + 1 >= len(args):
                raise Namel3ssError(
                    build_guidance_message(
                        what="--log flag is missing a value.",
                        why="Replay needs the explain log path when --log is provided.",
                        fix="Pass a JSON file path after --log.",
                        example="n3 replay --log .namel3ss/explain/last_explain.json",
                    )
                )
            log_path = Path(args[index + 1]).expanduser()
            index += 2
            continue
        if token.startswith("--"):
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Unknown replay flag '{token}'.",
                    why="Replay supports --log, --json, and --no-verify.",
                    fix="Remove the unsupported flag.",
                    example="n3 replay --json",
                )
            )
        if app_arg is None:
            app_arg = token
            index += 1
            continue
        raise Namel3ssError(
            build_guidance_message(
                what="Too many positional arguments for replay.",
                why="Replay accepts at most one app path.",
                fix="Pass only one app path or use --log.",
                example="n3 replay app.ai",
            )
        )
    return _ReplayParams(app_arg=app_arg, log_path=log_path, json_mode=json_mode, strict_hash=strict_hash)


def _resolve_log_path(params: _ReplayParams) -> Path:
    if params.log_path is not None:
        path = params.log_path.resolve()
    else:
        app_path = resolve_app_path(params.app_arg)
        path = (app_path.parent / ".namel3ss" / "explain" / "last_explain.json").resolve()
    if not path.exists():
        raise Namel3ssError(
            build_guidance_message(
                what=f"Replay log not found: {path}",
                why="Replay requires an existing explain log file.",
                fix="Run `n3 run --explain` first or pass --log with a valid path.",
                example="n3 replay --log .namel3ss/explain/last_explain.json",
            )
        )
    return path


def _build_replay_payload(log_path: Path, *, strict_hash: bool) -> dict[str, object]:
    raw_payload = _read_raw_payload(log_path)
    log_payload = load_explain_log(log_path)
    entries = raw_payload.get("entries")
    if not isinstance(entries, list):
        entries = []
    computed_hash = explain_replay_hash(entries if isinstance(entries, list) else [])
    stored_hash = str(raw_payload.get("replay_hash") or "")
    hash_verified = bool(stored_hash) and stored_hash == computed_hash
    if strict_hash and stored_hash and not hash_verified:
        raise Namel3ssError(
            build_guidance_message(
                what="Replay hash validation failed.",
                why="The explain log replay_hash does not match canonical entry content.",
                fix="Re-run the flow to regenerate logs or inspect the file for manual edits.",
                example="n3 run --explain app.ai",
            )
        )
    steps = [_step_payload(entry) for entry in entries if isinstance(entry, dict)]
    retrieval = [
        {
            "event_index": step.get("event_index"),
            "modality": step.get("retrieval_modality"),
            "selected": step.get("retrieval_selected"),
        }
        for step in steps
        if step.get("stage") == "retrieval"
    ]
    return {
        "ok": True,
        "log_path": log_path.as_posix(),
        "flow_name": str(raw_payload.get("flow_name") or log_payload.get("flow_name") or ""),
        "entry_count": len(steps),
        "stored_replay_hash": stored_hash,
        "computed_replay_hash": computed_hash,
        "hash_verified": hash_verified or not stored_hash,
        "seeds": _seed_list(steps),
        "retrieval_events": retrieval,
        "steps": steps,
    }


def _read_raw_payload(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        raise Namel3ssError(
            build_guidance_message(
                what="Replay log is not valid JSON.",
                why=str(err),
                fix="Regenerate explain logs with `n3 run --explain`.",
                example="n3 run --explain app.ai",
            )
        ) from err
    if isinstance(payload, dict):
        return payload
    return {}


def _step_payload(entry: dict[str, object]) -> dict[str, object]:
    metadata = entry.get("metadata")
    retrieval = metadata if isinstance(metadata, dict) and "selected" in metadata else {}
    return {
        "event_index": _safe_int(entry.get("event_index")),
        "timestamp": str(entry.get("timestamp") or ""),
        "stage": str(entry.get("stage") or ""),
        "event_type": str(entry.get("event_type") or ""),
        "seed": entry.get("seed"),
        "provider": str(entry.get("provider") or ""),
        "model": str(entry.get("model") or ""),
        "retrieval_modality": retrieval.get("modality") if isinstance(retrieval, dict) else None,
        "retrieval_selected": retrieval.get("selected") if isinstance(retrieval, dict) else None,
    }


def _seed_list(steps: list[dict[str, object]]) -> list[int | str]:
    output: list[int | str] = []
    for step in steps:
        seed = step.get("seed")
        if isinstance(seed, (int, str)) and seed not in output:
            output.append(seed)
    return output


def _safe_int(value: object) -> int:
    if isinstance(value, bool):
        return 0
    try:
        parsed = int(value)
    except Exception:
        return 0
    return parsed if parsed >= 0 else 0


def _print_human(payload: dict[str, object]) -> None:
    print(f"log: {payload.get('log_path')}")
    print(f"flow: {payload.get('flow_name')}")
    print(f"events: {payload.get('entry_count')}")
    print(f"hash verified: {payload.get('hash_verified')}")
    seeds = payload.get("seeds")
    if isinstance(seeds, list):
        if seeds:
            print("seeds: " + ", ".join(str(item) for item in seeds))
        else:
            print("seeds: none")
    retrieval = payload.get("retrieval_events")
    if isinstance(retrieval, list) and retrieval:
        print(f"retrieval events: {len(retrieval)}")
        first = retrieval[0]
        if isinstance(first, dict):
            print(f"first retrieval modality: {first.get('modality')}")
    else:
        print("retrieval events: 0")


__all__ = ["run_replay_command"]
