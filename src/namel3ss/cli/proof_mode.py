from __future__ import annotations

from dataclasses import dataclass

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.cli.proofs import write_proof
from namel3ss.cli.promotion_state import load_state
from namel3ss.cli.targets import parse_target
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.proofs import build_engine_proof
from namel3ss.secrets import set_audit_root, set_engine_target
from namel3ss.utils.json_tools import dumps_pretty


@dataclass
class _ProofParams:
    app_arg: str | None
    target_raw: str | None
    build_id: str | None
    json_mode: bool
    write: bool


def run_proof_command(args: list[str]) -> int:
    params = _parse_args(args)
    app_path = resolve_app_path(params.app_arg)
    project_root = app_path.parent
    target = _resolve_target(params.target_raw, project_root)
    set_engine_target(target)
    set_audit_root(project_root)
    proof_id, proof = build_engine_proof(app_path, target=target, build_id=params.build_id)
    proof_path = None
    if params.write:
        proof_path = write_proof(project_root, proof_id, proof)
    if params.json_mode:
        print(dumps_pretty(proof))
        return 0
    print(f"Engine proof: {proof_id}")
    if proof_path:
        print(f"Stored: {proof_path.as_posix()}")
    else:
        print("Stored: disabled (use --write to persist).")
    return 0


def _parse_args(args: list[str]) -> _ProofParams:
    app_arg = None
    target = None
    build_id = None
    json_mode = False
    write = True
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--target":
            if i + 1 >= len(args):
                raise Namel3ssError(
                    build_guidance_message(
                        what="--target flag is missing a value.",
                        why="Proof needs a target name.",
                        fix="Provide local, service, or edge.",
                        example="n3 proof --target service",
                    )
                )
            target = args[i + 1]
            i += 2
            continue
        if arg == "--build":
            if i + 1 >= len(args):
                raise Namel3ssError(
                    build_guidance_message(
                        what="--build flag is missing a value.",
                        why="A build id must follow --build.",
                        fix="Provide the build id.",
                        example="n3 proof --target service --build service-abc123",
                    )
                )
            build_id = args[i + 1]
            i += 2
            continue
        if arg == "--json":
            json_mode = True
            i += 1
            continue
        if arg == "--write":
            write = True
            i += 1
            continue
        if arg == "--no-write":
            write = False
            i += 1
            continue
        if arg.startswith("--"):
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Unknown flag '{arg}'.",
                    why="Supported flags: --target, --build, --json, --write.",
                    fix="Remove the unsupported flag.",
                    example="n3 proof --target local --json",
                )
            )
        if app_arg is None:
            app_arg = arg
            i += 1
            continue
        raise Namel3ssError(
            build_guidance_message(
                what="Too many positional arguments.",
                why="Proof accepts at most one app path.",
                fix="Provide a single app.ai path or none.",
                example="n3 proof app.ai",
            )
        )
    return _ProofParams(app_arg, target, build_id, json_mode, write)


def _resolve_target(target_raw: str | None, project_root) -> str:
    if target_raw:
        return parse_target(target_raw).name
    state = load_state(project_root)
    active = state.get("active") or {}
    if active.get("target"):
        return str(active.get("target"))
    return parse_target(None).name


__all__ = ["run_proof_command"]
