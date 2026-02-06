from __future__ import annotations

from pathlib import Path

from namel3ss.ir.model.program import Program
from namel3ss.ir import nodes as ir
from namel3ss.spec_check.engine_map import ENGINE_SUPPORTED_SPECS, SPEC_CAPABILITIES
from namel3ss.spec_check.model import SpecDecision, SpecPack
from namel3ss.spec_check.normalize import normalize_decision, normalize_list, write_spec_artifacts
from namel3ss.spec_check.render_plain import render_when
from namel3ss.runtime.providers.pack_registry import capability_for_provider


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
    if program.jobs:
        required.add("jobs")
    if _program_uses_scheduling(program):
        required.add("scheduling")
    if "scheduling" in program.capabilities:
        required.add("scheduling")
    if "uploads" in program.capabilities:
        required.add("uploads")
    if "embedding" in program.capabilities:
        required.add("embedding")
    if "vision" in program.capabilities:
        required.add("vision")
    if "speech" in program.capabilities:
        required.add("speech")
    for token in (
        "huggingface",
        "local_runner",
        "vision_gen",
        "third_party_apis",
        "training",
        "streaming",
        "performance",
        "performance_scalability",
    ):
        if token in program.capabilities:
            required.add(token)
    for ai in program.ais.values():
        provider = str(getattr(ai, "provider", "") or "").strip().lower()
        capability = capability_for_provider(provider)
        if capability:
            required.add(capability)
    for tool in program.tools.values():
        kind = getattr(tool, "kind", None)
        if kind == "http":
            required.add("http")
        elif kind == "file":
            required.add("files")
    if _program_uses_secrets(program):
        required.add("secrets")
    if "secrets" in program.capabilities:
        required.add("secrets")
    if _program_uses_ai_mode(program, "image"):
        required.add("vision")
    if _program_uses_ai_mode(program, "audio"):
        required.add("speech")
    if _program_uses_streaming(program):
        required.add("streaming")
    if program.agents:
        required.add("agents_v1")
    if program.identity is not None:
        required.add("identity_v1")
    if _theme_used(program):
        required.add("theme_v1")
    return tuple(sorted(required))


def _program_uses_scheduling(program: Program) -> bool:
    for flow in program.flows:
        if _statements_use_scheduling(flow.body):
            return True
    for job in program.jobs:
        if _statements_use_scheduling(job.body):
            return True
    return False


def _statements_use_scheduling(statements: list[ir.Statement]) -> bool:
    for stmt in statements:
        if isinstance(stmt, ir.AdvanceTime):
            return True
        if isinstance(stmt, ir.EnqueueJob) and stmt.schedule_kind:
            return True
        if isinstance(stmt, ir.If):
            if _statements_use_scheduling(stmt.then_body) or _statements_use_scheduling(stmt.else_body):
                return True
        if isinstance(stmt, ir.Repeat):
            if _statements_use_scheduling(stmt.body):
                return True
        if isinstance(stmt, ir.RepeatWhile):
            if _statements_use_scheduling(stmt.body):
                return True
        if isinstance(stmt, ir.ForEach):
            if _statements_use_scheduling(stmt.body):
                return True
        if isinstance(stmt, ir.Match):
            if any(_statements_use_scheduling(case.body) for case in stmt.cases):
                return True
            if stmt.otherwise and _statements_use_scheduling(stmt.otherwise):
                return True
        if isinstance(stmt, ir.TryCatch):
            if _statements_use_scheduling(stmt.try_body) or _statements_use_scheduling(stmt.catch_body):
                return True
        if isinstance(stmt, ir.RunAgentsParallelStmt):
            continue
        if isinstance(stmt, ir.ParallelBlock):
            if any(_statements_use_scheduling(task.body) for task in stmt.tasks):
                return True
    return False


def _program_uses_secrets(program: Program) -> bool:
    for flow in program.flows:
        if _statements_use_secrets(flow.body):
            return True
    for job in program.jobs:
        if _statements_use_secrets(job.body):
            return True
        if job.when is not None and _expression_uses_secrets(job.when):
            return True
    for func in program.functions.values():
        if _statements_use_secrets(func.body):
            return True
    return False


def _program_uses_ai_mode(program: Program, mode: str) -> bool:
    for flow in program.flows:
        if _statements_use_ai_mode(flow.body, mode):
            return True
    for job in program.jobs:
        if _statements_use_ai_mode(job.body, mode):
            return True
    for func in program.functions.values():
        if _statements_use_ai_mode(func.body, mode):
            return True
    return False


def _statements_use_ai_mode(statements: list[ir.Statement], mode: str) -> bool:
    expected = mode.strip().lower()
    for stmt in statements:
        if isinstance(stmt, ir.AskAIStmt):
            if str(getattr(stmt, "input_mode", "text")).strip().lower() == expected:
                return True
        if isinstance(stmt, ir.RunAgentStmt):
            if str(getattr(stmt, "input_mode", "text")).strip().lower() == expected:
                return True
        if isinstance(stmt, ir.RunAgentsParallelStmt):
            if any(str(getattr(entry, "input_mode", "text")).strip().lower() == expected for entry in stmt.entries):
                return True
        if isinstance(stmt, ir.If):
            if _statements_use_ai_mode(stmt.then_body, mode) or _statements_use_ai_mode(stmt.else_body, mode):
                return True
        if isinstance(stmt, ir.Repeat):
            if _statements_use_ai_mode(stmt.body, mode):
                return True
        if isinstance(stmt, ir.RepeatWhile):
            if _statements_use_ai_mode(stmt.body, mode):
                return True
        if isinstance(stmt, ir.ForEach):
            if _statements_use_ai_mode(stmt.body, mode):
                return True
        if isinstance(stmt, ir.Match):
            if any(_statements_use_ai_mode(case.body, mode) for case in stmt.cases):
                return True
            if stmt.otherwise and _statements_use_ai_mode(stmt.otherwise, mode):
                return True
        if isinstance(stmt, ir.TryCatch):
            if _statements_use_ai_mode(stmt.try_body, mode) or _statements_use_ai_mode(stmt.catch_body, mode):
                return True
        if isinstance(stmt, ir.ParallelBlock):
            if any(_statements_use_ai_mode(task.body, mode) for task in stmt.tasks):
                return True
    return False


def _program_uses_streaming(program: Program) -> bool:
    for flow in program.flows:
        if _statements_use_streaming(flow.body):
            return True
    for job in program.jobs:
        if _statements_use_streaming(job.body):
            return True
    for func in program.functions.values():
        if _statements_use_streaming(func.body):
            return True
    return False


def _statements_use_streaming(statements: list[ir.Statement]) -> bool:
    for stmt in statements:
        if isinstance(stmt, ir.AskAIStmt):
            if bool(getattr(stmt, "stream", False)):
                return True
        if isinstance(stmt, ir.If):
            if _statements_use_streaming(stmt.then_body) or _statements_use_streaming(stmt.else_body):
                return True
        if isinstance(stmt, ir.Repeat):
            if _statements_use_streaming(stmt.body):
                return True
        if isinstance(stmt, ir.RepeatWhile):
            if _statements_use_streaming(stmt.body):
                return True
        if isinstance(stmt, ir.ForEach):
            if _statements_use_streaming(stmt.body):
                return True
        if isinstance(stmt, ir.Match):
            if any(_statements_use_streaming(case.body) for case in stmt.cases):
                return True
            if stmt.otherwise and _statements_use_streaming(stmt.otherwise):
                return True
        if isinstance(stmt, ir.TryCatch):
            if _statements_use_streaming(stmt.try_body) or _statements_use_streaming(stmt.catch_body):
                return True
        if isinstance(stmt, ir.ParallelBlock):
            if any(_statements_use_streaming(task.body) for task in stmt.tasks):
                return True
    return False


def _statements_use_secrets(statements: list[ir.Statement]) -> bool:
    for stmt in statements:
        if isinstance(stmt, (ir.Let, ir.Set, ir.Return)):
            if _expression_uses_secrets(stmt.expression):
                return True
        if isinstance(stmt, ir.If):
            if _expression_uses_secrets(stmt.condition):
                return True
            if _statements_use_secrets(stmt.then_body) or _statements_use_secrets(stmt.else_body):
                return True
        if isinstance(stmt, ir.Repeat):
            if _expression_uses_secrets(stmt.count) or _statements_use_secrets(stmt.body):
                return True
        if isinstance(stmt, ir.RepeatWhile):
            if _expression_uses_secrets(stmt.condition) or _statements_use_secrets(stmt.body):
                return True
        if isinstance(stmt, ir.ForEach):
            if _expression_uses_secrets(stmt.iterable) or _statements_use_secrets(stmt.body):
                return True
        if isinstance(stmt, ir.Match):
            if _expression_uses_secrets(stmt.expression):
                return True
            for case in stmt.cases:
                if _expression_uses_secrets(case.pattern) or _statements_use_secrets(case.body):
                    return True
            if stmt.otherwise and _statements_use_secrets(stmt.otherwise):
                return True
        if isinstance(stmt, ir.TryCatch):
            if _statements_use_secrets(stmt.try_body) or _statements_use_secrets(stmt.catch_body):
                return True
        if isinstance(stmt, ir.AskAIStmt):
            if _expression_uses_secrets(stmt.input_expr):
                return True
        if isinstance(stmt, ir.RunAgentStmt):
            if _expression_uses_secrets(stmt.input_expr):
                return True
        if isinstance(stmt, ir.RunAgentsParallelStmt):
            if any(_expression_uses_secrets(entry.input_expr) for entry in stmt.entries):
                return True
        if isinstance(stmt, ir.ParallelBlock):
            if any(_statements_use_secrets(task.body) for task in stmt.tasks):
                return True
        if isinstance(stmt, ir.Create):
            if _expression_uses_secrets(stmt.values):
                return True
        if isinstance(stmt, ir.Find):
            if _expression_uses_secrets(stmt.predicate):
                return True
        if isinstance(stmt, ir.Update):
            if _expression_uses_secrets(stmt.predicate):
                return True
            if any(_expression_uses_secrets(update.expression) for update in stmt.updates):
                return True
        if isinstance(stmt, ir.Delete):
            if _expression_uses_secrets(stmt.predicate):
                return True
        if isinstance(stmt, ir.EnqueueJob):
            if stmt.input_expr is not None and _expression_uses_secrets(stmt.input_expr):
                return True
            if stmt.schedule_expr is not None and _expression_uses_secrets(stmt.schedule_expr):
                return True
        if isinstance(stmt, ir.AdvanceTime):
            if _expression_uses_secrets(stmt.amount):
                return True
        if isinstance(stmt, ir.LogStmt):
            if _expression_uses_secrets(stmt.message):
                return True
            if stmt.fields is not None and _expression_uses_secrets(stmt.fields):
                return True
        if isinstance(stmt, ir.MetricStmt):
            if stmt.value is not None and _expression_uses_secrets(stmt.value):
                return True
            if stmt.labels is not None and _expression_uses_secrets(stmt.labels):
                return True
    return False


def _expression_uses_secrets(expr: ir.Expression) -> bool:
    if isinstance(expr, ir.BuiltinCallExpr):
        if expr.name in {"secret", "auth_bearer", "auth_basic", "auth_header"}:
            return True
        return any(_expression_uses_secrets(arg) for arg in expr.arguments)
    if isinstance(expr, ir.ToolCallExpr):
        return any(_expression_uses_secrets(arg.value) for arg in expr.arguments)
    if isinstance(expr, ir.CallFunctionExpr):
        return any(_expression_uses_secrets(arg.value) for arg in expr.arguments)
    if isinstance(expr, ir.UnaryOp):
        return _expression_uses_secrets(expr.operand)
    if isinstance(expr, ir.BinaryOp):
        return _expression_uses_secrets(expr.left) or _expression_uses_secrets(expr.right)
    if isinstance(expr, ir.Comparison):
        return _expression_uses_secrets(expr.left) or _expression_uses_secrets(expr.right)
    if isinstance(expr, ir.ListExpr):
        return any(_expression_uses_secrets(item) for item in expr.items)
    if isinstance(expr, ir.MapExpr):
        return any(
            _expression_uses_secrets(entry.key) or _expression_uses_secrets(entry.value)
            for entry in expr.entries
        )
    if isinstance(expr, ir.ListOpExpr):
        if _expression_uses_secrets(expr.target):
            return True
        if expr.value is not None and _expression_uses_secrets(expr.value):
            return True
        if expr.index is not None and _expression_uses_secrets(expr.index):
            return True
        return False
    if isinstance(expr, ir.MapOpExpr):
        if _expression_uses_secrets(expr.target):
            return True
        if expr.key is not None and _expression_uses_secrets(expr.key):
            return True
        if expr.value is not None and _expression_uses_secrets(expr.value):
            return True
        return False
    if isinstance(expr, ir.ListMapExpr):
        return _expression_uses_secrets(expr.target) or _expression_uses_secrets(expr.body)
    if isinstance(expr, ir.ListFilterExpr):
        return _expression_uses_secrets(expr.target) or _expression_uses_secrets(expr.predicate)
    if isinstance(expr, ir.ListReduceExpr):
        return (
            _expression_uses_secrets(expr.target)
            or _expression_uses_secrets(expr.start)
            or _expression_uses_secrets(expr.body)
        )
    return False


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
