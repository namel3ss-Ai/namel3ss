from __future__ import annotations

import json
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ir.model.program import Program
from namel3ss.spec_check.builder import build_spec_pack, derive_required_capabilities
from namel3ss.spec_check.model import SpecDecision, SpecPack


def check_spec_for_program(program: Program, declared_spec: str) -> SpecPack:
    if not declared_spec:
        raise _missing_spec_error()
    required = derive_required_capabilities(program)
    return build_spec_pack(
        declared_spec=declared_spec,
        required_capabilities=required,
        project_root=_resolve_root(program),
    )


def enforce_spec_for_program(program: Program, declared_spec: str) -> None:
    pack = check_spec_for_program(program, declared_spec)
    if pack.decision.status == "blocked":
        raise Namel3ssError(_decision_message(pack.decision))


def load_spec_pack(path: Path) -> SpecPack | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    decision_data = payload.get("decision")
    if not isinstance(decision_data, dict):
        return None
    decision = _decision_from_dict(decision_data)
    if decision is None:
        return None
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    return SpecPack(decision=decision, summary=summary)


def _decision_from_dict(value: dict) -> SpecDecision | None:
    try:
        return SpecDecision(
            status=str(value.get("status") or ""),
            declared_spec=str(value.get("declared_spec") or ""),
            engine_supported=tuple(value.get("engine_supported") or []),
            required_capabilities=tuple(value.get("required_capabilities") or []),
            unsupported_capabilities=tuple(value.get("unsupported_capabilities") or []),
            what=str(value.get("what") or ""),
            why=tuple(value.get("why") or []),
            fix=tuple(value.get("fix") or []),
            example=value.get("example") if isinstance(value.get("example"), str) else None,
        )
    except Exception:
        return None


def _decision_message(decision: SpecDecision) -> str:
    why = "; ".join(decision.why) if decision.why else "Spec check blocked."
    fix = " ".join(decision.fix) if decision.fix else "Update the spec version or adjust the program."
    example = decision.example or 'spec is "1.0"'
    return build_guidance_message(what=decision.what, why=why, fix=fix, example=example)


def _missing_spec_error() -> Namel3ssError:
    return Namel3ssError(
        build_guidance_message(
            what="Spec declaration is missing.",
            why="Every program must declare the spec version at the root.",
            fix='Add a spec declaration at the top of the file.',
            example='spec is "1.0"',
        )
    )


def _resolve_root(program: Program) -> Path | None:
    project_root = getattr(program, "project_root", None)
    if isinstance(project_root, Path):
        return project_root
    if isinstance(project_root, str) and project_root:
        return Path(project_root)
    app_path = getattr(program, "app_path", None)
    if isinstance(app_path, Path):
        return app_path.parent
    if isinstance(app_path, str) and app_path:
        return Path(app_path).parent
    return Path.cwd()


__all__ = ["check_spec_for_program", "enforce_spec_for_program", "load_spec_pack"]
