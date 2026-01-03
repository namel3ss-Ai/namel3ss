from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.format.formatter import format_source
from namel3ss.lexer.lexer import Lexer
from namel3ss.spec_check.api import check_spec_for_program
from namel3ss.spec_check.engine_map import ENGINE_SUPPORTED_SPECS
from namel3ss.spec_check.extract import extract_declared_spec


LATEST_SPEC_VERSION = ENGINE_SUPPORTED_SPECS[0] if ENGINE_SUPPORTED_SPECS else "1.0"
MIGRATION_TARGETS: dict[str, str] = {
    "0.9": LATEST_SPEC_VERSION,
}
_SPEC_DECL_RE = re.compile(r'^(?P<prefix>\s*spec\s+is\s+")(?P<version>[^"]+)("\s*)$', re.IGNORECASE)
_MIGRATION_PIPELINE = {
    ("0.9", LATEST_SPEC_VERSION): ("format", "spec"),
}


@dataclass(frozen=True)
class MigrationPlan:
    from_version: str
    to_version: str
    steps: tuple[str, ...]


@dataclass(frozen=True)
class MigrationResult:
    source: str
    changed: bool
    plan: MigrationPlan


def validate_spec_version(program) -> None:
    declared = str(getattr(program, "spec_version", "") or "")
    if not declared:
        raise _missing_spec_error()
    pack = check_spec_for_program(program, declared)
    if pack.decision.status == "compatible":
        return
    target = MIGRATION_TARGETS.get(declared)
    if target:
        raise _spec_migration_required(declared, target, pack.decision.engine_supported)
    raise _spec_unsupported(declared, pack.decision.engine_supported)


def plan_migration(source: str, *, from_version: str | None, to_version: str | None) -> MigrationPlan:
    declared = from_version or detect_declared_spec(source)
    target = to_version or MIGRATION_TARGETS.get(declared) or LATEST_SPEC_VERSION
    if declared == target:
        return MigrationPlan(from_version=declared, to_version=target, steps=())
    steps = _MIGRATION_PIPELINE.get((declared, target))
    if not steps:
        raise Namel3ssError(_unsupported_migration_message(declared, target))
    return MigrationPlan(from_version=declared, to_version=target, steps=tuple(steps))


def apply_migration(source: str, plan: MigrationPlan) -> MigrationResult:
    updated = source
    for step in plan.steps:
        if step == "format":
            updated = format_source(updated)
            continue
        if step == "spec":
            updated = _replace_spec_version(updated, plan.to_version)
            continue
        raise Namel3ssError(f"Unknown migration step: {step}")
    if plan.steps:
        updated = _replace_spec_version(updated, plan.to_version)
    changed = updated != source
    return MigrationResult(source=updated, changed=changed, plan=plan)


def detect_declared_spec(source: str) -> str:
    tokens = Lexer(source).tokenize()
    return extract_declared_spec(tokens)


def _replace_spec_version(source: str, target: str) -> str:
    lines = source.splitlines()
    matches = []
    for idx, line in enumerate(lines):
        match = _SPEC_DECL_RE.match(line)
        if match:
            matches.append((idx, match))
    if not matches:
        raise _missing_spec_error()
    if len(matches) > 1:
        raise Namel3ssError(_duplicate_spec_message())
    idx, match = matches[0]
    current = match.group("version")
    if current == target:
        return source
    lines[idx] = f'{match.group("prefix")}{target}"'
    updated = "\n".join(lines)
    if source.endswith("\n") and not updated.endswith("\n"):
        updated += "\n"
    return updated


def _spec_unsupported(declared: str, supported: tuple[str, ...]) -> Namel3ssError:
    example = f'spec is "{supported[0]}"' if supported else 'spec is "1.0"'
    message = build_guidance_message(
        what=f'Spec version "{declared}" is not supported.',
        why=f"Engine supports: {', '.join(supported) if supported else 'none recorded'}.",
        fix="Update the spec version to a supported value.",
        example=example,
    )
    return Namel3ssError(
        message,
        details={
            "category": "policy",
            "code": "spec.unsupported",
            "declared_spec": declared,
            "supported_specs": list(supported),
        },
    )


def _spec_migration_required(declared: str, target: str, supported: tuple[str, ...]) -> Namel3ssError:
    message = build_guidance_message(
        what=f'Spec version "{declared}" requires migration.',
        why=f"Engine supports: {', '.join(supported) if supported else 'none recorded'}.",
        fix=f'Run n3 migrate --from {declared} --to {target}.',
        example=f'n3 migrate --from {declared} --to {target}',
    )
    return Namel3ssError(
        message,
        details={
            "category": "policy",
            "code": "spec.migration_required",
            "declared_spec": declared,
            "target_spec": target,
            "supported_specs": list(supported),
        },
    )


def _missing_spec_error() -> Namel3ssError:
    return Namel3ssError(
        build_guidance_message(
            what="Spec declaration is missing.",
            why="Every program must declare the spec version at the root.",
            fix='Add a spec declaration at the top of the file.',
            example='spec is "1.0"',
        ),
        details={"category": "parse", "code": "spec.missing"},
    )


def _duplicate_spec_message() -> str:
    return build_guidance_message(
        what="Spec is declared more than once.",
        why="The spec declaration must appear only once at the program root.",
        fix="Keep a single spec declaration.",
        example='spec is "1.0"',
    )


def _unsupported_migration_message(from_version: str, to_version: str) -> str:
    return build_guidance_message(
        what="Requested spec migration is not supported.",
        why=f"No migration path from {from_version} to {to_version}.",
        fix="Choose a supported target version.",
        example=f"n3 migrate --from {from_version} --to {LATEST_SPEC_VERSION}",
    )


__all__ = [
    "LATEST_SPEC_VERSION",
    "MigrationPlan",
    "MigrationResult",
    "apply_migration",
    "detect_declared_spec",
    "plan_migration",
    "validate_spec_version",
]
