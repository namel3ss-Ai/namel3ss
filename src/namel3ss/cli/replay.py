from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.cli.replay_mode import run_replay_command as run_explain_replay
from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.audit.audit_bundle import resolve_audit_artifact_path
from namel3ss.runtime.audit.replay_engine import replay_run_artifact_file


@dataclass(frozen=True)
class _ReplayParams:
    app_arg: str | None
    artifact_path: str | None
    json_mode: bool
    strict: bool


def run_replay_command(args: list[str]) -> int:
    if _use_legacy_replay(args):
        return run_explain_replay(args)
    params = _parse_args(args)
    artifact_path = _resolve_artifact_path(params)
    payload = replay_run_artifact_file(artifact_path)
    if params.strict and not bool(payload.get("ok")):
        raise Namel3ssError(
            build_guidance_message(
                what="Replay verification failed.",
                why="The stored run artifact does not match deterministic replay checks.",
                fix="Inspect mismatches in the replay output and regenerate the run artifact.",
                example="n3 replay --artifact .namel3ss/audit/last/run_artifact.json --json",
            )
        )
    if params.json_mode:
        print(canonical_json_dumps(payload, pretty=True, drop_run_keys=False))
    else:
        _print_human(payload)
    return 0


def _use_legacy_replay(args: list[str]) -> bool:
    if "--log" in args:
        return True
    if "--artifact" in args:
        return False
    positional = [arg for arg in args if not arg.startswith("--")]
    if not positional:
        return True
    first = positional[0]
    if first.endswith(".json"):
        return False
    return True


def _parse_args(args: list[str]) -> _ReplayParams:
    app_arg: str | None = None
    artifact_path: str | None = None
    json_mode = False
    strict = True
    index = 0
    while index < len(args):
        token = args[index]
        if token == "--json":
            json_mode = True
            index += 1
            continue
        if token == "--no-verify":
            strict = False
            index += 1
            continue
        if token == "--artifact":
            if index + 1 >= len(args):
                raise Namel3ssError(
                    build_guidance_message(
                        what="--artifact flag is missing a value.",
                        why="Replay needs a run artifact path when --artifact is provided.",
                        fix="Pass a JSON path after --artifact.",
                        example="n3 replay --artifact .namel3ss/audit/last/run_artifact.json",
                    )
                )
            artifact_path = args[index + 1]
            index += 2
            continue
        if token.startswith("--"):
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Unknown replay flag '{token}'.",
                    why="Replay supports --artifact, --json, and --no-verify.",
                    fix="Remove unsupported flags.",
                    example="n3 replay --artifact .namel3ss/audit/last/run_artifact.json --json",
                )
            )
        if token.endswith(".json"):
            artifact_path = token
            index += 1
            continue
        if app_arg is None:
            app_arg = token
            index += 1
            continue
        raise Namel3ssError(
            build_guidance_message(
                what="Too many positional arguments for replay.",
                why="Replay accepts at most one app path and one artifact path.",
                fix="Pass a single app path or artifact path.",
                example="n3 replay app.ai --artifact .namel3ss/audit/last/run_artifact.json",
            )
        )
    return _ReplayParams(app_arg=app_arg, artifact_path=artifact_path, json_mode=json_mode, strict=strict)


def _resolve_artifact_path(params: _ReplayParams) -> Path:
    if params.artifact_path:
        path = Path(params.artifact_path).expanduser().resolve()
    else:
        app_path = resolve_app_path(params.app_arg)
        path = resolve_audit_artifact_path(app_path.parent)
    if not path.exists():
        raise Namel3ssError(
            build_guidance_message(
                what=f"Replay artifact not found: {path}",
                why="Replay requires a run artifact JSON file.",
                fix="Run a flow/action first or pass --artifact with a valid path.",
                example="n3 replay --artifact .namel3ss/audit/last/run_artifact.json",
            )
        )
    return path


def _print_human(payload: dict[str, object]) -> None:
    print(f"artifact: {payload.get('artifact_path')}")
    print(f"run id: {payload.get('run_id')}")
    print(f"ok: {payload.get('ok')}")
    mismatches = payload.get("mismatches")
    if isinstance(mismatches, list) and mismatches:
        print(f"mismatches: {len(mismatches)}")
        first = mismatches[0]
        if isinstance(first, dict):
            print(f"first mismatch: {first.get('field')}")
    else:
        print("mismatches: 0")


__all__ = ["run_replay_command"]
