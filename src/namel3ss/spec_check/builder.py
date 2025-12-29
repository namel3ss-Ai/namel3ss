from __future__ import annotations

from pathlib import Path

from namel3ss.ir.model.program import Program
from namel3ss.spec_check.engine_map import ENGINE_SUPPORTED_SPECS, SPEC_CAPABILITIES
from namel3ss.spec_check.model import SpecDecision, SpecPack
from namel3ss.spec_check.normalize import normalize_decision, normalize_list, write_spec_artifacts
from namel3ss.spec_check.render_plain import render_when


def derive_required_capabilities(program: Program) -> tuple[str, ...]:
    required: set[str] = set()
    if program.records:
        required.add("records_v1")
    if program.pages:
        required.add("pages_v1")
    if program.ais:
        required.add("ai_v1")
    if program.tools:
        required.add("tools_v1")
    if program.agents:
        required.add("agents_v1")
    if program.identity is not None:
        required.add("identity_v1")
    if _theme_used(program):
        required.add("theme_v1")
    return tuple(sorted(required))


def build_spec_pack(
    *,
    declared_spec: str,
    required_capabilities: tuple[str, ...],
    project_root: str | Path | None = None,
) -> SpecPack:
    engine_supported = normalize_list(ENGINE_SUPPORTED_SPECS)
    required = normalize_list(required_capabilities)
    preferred_spec = engine_supported[0] if engine_supported else ""

    if declared_spec not in ENGINE_SUPPORTED_SPECS:
        decision = SpecDecision(
            status="blocked",
            declared_spec=declared_spec,
            engine_supported=engine_supported,
            required_capabilities=required,
            unsupported_capabilities=(),
            what=f'Spec version "{declared_spec}" is not supported.',
            why=(
                f"Engine supports: {', '.join(engine_supported) if engine_supported else 'none recorded'}.",
            ),
            fix=("Update the spec version to a supported value.",),
            example=f'spec is "{preferred_spec}"' if preferred_spec else None,
        )
    else:
        supported = SPEC_CAPABILITIES.get(declared_spec, frozenset())
        unsupported = tuple(sorted(set(required) - set(supported)))
        if unsupported:
            decision = SpecDecision(
                status="blocked",
                declared_spec=declared_spec,
                engine_supported=engine_supported,
                required_capabilities=required,
                unsupported_capabilities=unsupported,
                what=f'Spec version "{declared_spec}" does not support required capabilities.',
                why=(f"Unsupported capabilities: {', '.join(unsupported)}.",),
                fix=(
                    "Use a spec version that supports these capabilities or remove the unsupported features.",
                ),
                example=f'spec is "{preferred_spec}"' if preferred_spec else None,
            )
        else:
            decision = SpecDecision(
                status="compatible",
                declared_spec=declared_spec,
                engine_supported=engine_supported,
                required_capabilities=required,
                unsupported_capabilities=(),
                what=f'Spec version "{declared_spec}" is compatible.',
                why=("All required capabilities are supported.",),
                fix=(),
                example=None,
            )

    normalized = normalize_decision(decision)
    summary = {"status": normalized.status, "declared_spec": normalized.declared_spec}
    pack = SpecPack(decision=normalized, summary=summary)

    root = _resolve_root(project_root)
    if root is not None:
        plain_text = render_when(pack)
        try:
            write_spec_artifacts(root, pack, plain_text, plain_text)
        except Exception:
            pass

    return pack


def _theme_used(program: Program) -> bool:
    if program.theme and program.theme != "system":
        return True
    if program.theme_tokens:
        return True
    if getattr(program, "theme_runtime_supported", False):
        return True
    preference = getattr(program, "theme_preference", {}) or {}
    if preference.get("allow_override", False):
        return True
    if preference.get("persist", "none") != "none":
        return True
    return False


def _resolve_root(project_root: str | Path | None) -> Path | None:
    if isinstance(project_root, Path):
        return project_root
    if isinstance(project_root, str) and project_root:
        return Path(project_root)
    return Path.cwd()


__all__ = ["build_spec_pack", "derive_required_capabilities"]
