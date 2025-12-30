from __future__ import annotations

import json
from pathlib import Path

from namel3ss.cli.app_loader import load_program
from namel3ss.cli.app_path import resolve_app_path
from namel3ss.config.loader import load_config
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.identity.context import resolve_identity
from namel3ss.runtime.memory.api import MemoryManager, explain_last, recall_with_events
from namel3ss.runtime.storage.factory import resolve_store
from namel3ss.utils.json_tools import dumps as json_dumps


def run_memory_command(args: list[str]) -> int:
    if not args:
        raise Namel3ssError(
            build_guidance_message(
                what="Memory command needs input.",
                why="memory expects text, why, or show.",
                fix='Run n3 memory "hello".',
                example='n3 memory "hello"',
            )
        )
    if args[0] == "why":
        output_json = _parse_why_args(args)
        _run_why(output_json)
        return 0
    if args[0] == "show":
        _ensure_no_extra_args(args, "show")
        _run_show()
        return 0
    selector, text = _parse_recall_args(args)
    _run_recall(selector, text)
    return 0


def _ensure_no_extra_args(args: list[str], action: str) -> None:
    if len(args) > 1:
        raise Namel3ssError(
            build_guidance_message(
                what=f"Too many arguments for memory {action}.",
                why=f"memory {action} does not accept extra input.",
                fix=f"Run n3 memory {action}.",
                example=f"n3 memory {action}",
            )
        )


def _parse_why_args(args: list[str]) -> bool:
    if len(args) == 1:
        return False
    if len(args) == 2 and args[1] == "--json":
        return True
    raise Namel3ssError(
        build_guidance_message(
            what="Unknown option for memory why.",
            why="The only supported option is --json.",
            fix="Run n3 memory why or n3 memory why --json.",
            example="n3 memory why --json",
        )
    )


def _parse_recall_args(args: list[str]) -> tuple[str | None, str]:
    selector = None
    text_parts = list(args)
    if text_parts[0].startswith("@"):
        selector = text_parts[0][1:]
        if not selector:
            raise Namel3ssError(
                build_guidance_message(
                    what="AI selector is empty.",
                    why="Selectors start with @name.",
                    fix='Use n3 memory @assistant "hello".',
                    example='n3 memory @assistant "hello"',
                )
            )
        text_parts = text_parts[1:]
    if not text_parts:
        raise Namel3ssError(
            build_guidance_message(
                what="Missing memory input text.",
                why="memory recall needs text to search.",
                fix='Provide input text: n3 memory "hello".',
                example='n3 memory "hello"',
            )
        )
    text = " ".join(text_parts).strip()
    if not text:
        raise Namel3ssError(
            build_guidance_message(
                what="Memory input text is empty.",
                why="memory recall needs text to search.",
                fix='Provide input text: n3 memory "hello".',
                example='n3 memory "hello"',
            )
        )
    return selector, text


def _run_recall(selector: str | None, text: str) -> None:
    app_path = resolve_app_path(None)
    program_ir, _sources = load_program(app_path.as_posix())
    project_root = Path(getattr(program_ir, "project_root", app_path.parent))
    config = load_config(app_path=app_path, root=project_root)
    store = resolve_store(None, config=config)
    state = store.load_state() or {}
    identity = resolve_identity(config, getattr(program_ir, "identity", None))
    ai_profile = _select_ai_profile(program_ir, selector)
    manager = MemoryManager(project_root=str(project_root), app_path=str(app_path))
    pack = recall_with_events(
        manager,
        ai_profile,
        text,
        state,
        identity=identity,
        project_root=str(project_root),
        app_path=str(app_path),
    )
    plain_text = _build_plain_text(pack)
    _write_last_run(project_root, pack, plain_text)
    print(pack.summary)
    counts = _count_context(pack.payload)
    total = sum(counts.values())
    recap = (
        f"Recalled: {total} items. "
        f"short_term {counts['short_term']}, semantic {counts['semantic']}, profile {counts['profile']}."
    )
    print(recap)


def _run_why(output_json: bool) -> None:
    app_path = resolve_app_path(None)
    project_root = Path(app_path).parent
    last_json = project_root / ".namel3ss" / "memory" / "last.json"
    if not last_json.exists():
        print('No memory run found yet. Try: n3 memory "hello"')
        return
    payload = json.loads(last_json.read_text(encoding="utf-8"))
    result = explain_last(payload)
    _write_last_why(project_root, result)
    if output_json:
        print(json_dumps(result, indent=2, sort_keys=True))
        return
    print(result.get("text", "").rstrip())


def _run_show() -> None:
    app_path = resolve_app_path(None)
    project_root = Path(app_path).parent
    last_plain = project_root / ".namel3ss" / "memory" / "last.plain"
    if not last_plain.exists():
        print('No memory run found yet. Try: n3 memory "hello"')
        return
    print(last_plain.read_text(encoding="utf-8").rstrip())


def _select_ai_profile(program_ir, selector: str | None):
    ai_profiles = getattr(program_ir, "ais", {}) or {}
    if not ai_profiles:
        raise Namel3ssError("No AI profiles found for this app.")
    if selector:
        if selector not in ai_profiles:
            available = ", ".join(sorted(ai_profiles.keys()))
            raise Namel3ssError(
                build_guidance_message(
                    what=f"AI profile '{selector}' was not found.",
                    why=f"Available profiles: {available}.",
                    fix='Pick one: n3 memory @name "hello".',
                    example=f'n3 memory @{sorted(ai_profiles.keys())[0]} "hello"',
                )
            )
        return ai_profiles[selector]
    if len(ai_profiles) == 1:
        return next(iter(ai_profiles.values()))
    if "assistant" in ai_profiles:
        return ai_profiles["assistant"]
    available = ", ".join(sorted(ai_profiles.keys()))
    raise Namel3ssError(
        build_guidance_message(
            what=f"Multiple AI profiles found: {available}.",
            why="Memory recall needs one profile.",
            fix='Pick one: n3 memory @name "hello".',
            example=f'n3 memory @{sorted(ai_profiles.keys())[0]} "hello"',
        )
    )


def _write_last_run(project_root: Path, pack, plain_text: str) -> None:
    memory_dir = project_root / ".namel3ss" / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)
    last_json = memory_dir / "last.json"
    last_plain = memory_dir / "last.plain"
    last_json.write_text(json_dumps(pack.as_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    last_plain.write_text(plain_text.rstrip() + "\n", encoding="utf-8")


def _write_last_why(project_root: Path, result: dict) -> None:
    memory_dir = project_root / ".namel3ss" / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)
    last_why = memory_dir / "last.why.txt"
    last_graph = memory_dir / "last.graph.json"
    text = result.get("text", "")
    graph = result.get("graph", {})
    last_why.write_text(text.rstrip() + "\n", encoding="utf-8")
    last_graph.write_text(json_dumps(graph, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _build_plain_text(pack) -> str:
    meta = pack.meta or {}
    proof = pack.proof or {}
    lines: list[str] = []
    counts = _count_context(pack.payload)
    total = sum(counts.values())
    lines.append(f"summary: {pack.summary}")
    lines.append(f"recalled.total: {total}")
    lines.append(f"recalled.short_term: {counts['short_term']}")
    lines.append(f"recalled.semantic: {counts['semantic']}")
    lines.append(f"recalled.profile: {counts['profile']}")
    recall_hash = proof.get("recall_hash")
    if recall_hash:
        lines.append(f"proof.recall_hash: {recall_hash}")
    phase_mode = proof.get("phase_mode")
    if phase_mode:
        lines.append(f"phase.mode: {phase_mode}")
    spaces = meta.get("spaces_consulted")
    if isinstance(spaces, list) and spaces:
        lines.append(f"spaces.consulted: {', '.join(spaces)}")
    recall_counts = meta.get("recall_counts") or {}
    if isinstance(recall_counts, dict):
        for space in sorted(recall_counts.keys()):
            lines.append(f"recall.{space}: {recall_counts.get(space)}")
    phase_counts = meta.get("phase_counts") or {}
    if isinstance(phase_counts, dict):
        for space in sorted(phase_counts.keys()):
            counts_by_phase = phase_counts.get(space) or {}
            for phase_id in sorted(counts_by_phase.keys()):
                lines.append(f"phase.{space}.{phase_id}: {counts_by_phase.get(phase_id)}")
    current_phase = meta.get("current_phase") or {}
    if isinstance(current_phase, dict) and current_phase.get("phase_id"):
        lines.append(f"phase.current: {current_phase.get('phase_id')}")
    return "\n".join(lines)


def _count_context(context: dict) -> dict[str, int]:
    return {
        "short_term": len(context.get("short_term", []) or []),
        "semantic": len(context.get("semantic", []) or []),
        "profile": len(context.get("profile", []) or []),
    }


__all__ = ["run_memory_command"]
