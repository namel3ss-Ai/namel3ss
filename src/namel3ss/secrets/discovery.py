from __future__ import annotations

from pathlib import Path
from typing import Iterable

from namel3ss.config.dotenv import load_dotenv_for_path
from namel3ss.config.model import AppConfig
from namel3ss.ir import nodes as ir
from namel3ss.secrets.model import SecretRef
from namel3ss.runtime.secrets_store import normalize_secret_name


PROVIDER_ENV = {
    "openai": "NAMEL3SS_OPENAI_API_KEY",
    "anthropic": "NAMEL3SS_ANTHROPIC_API_KEY",
    "gemini": "NAMEL3SS_GEMINI_API_KEY",
    "mistral": "NAMEL3SS_MISTRAL_API_KEY",
}

_ENV_ALIASES: dict[str, tuple[str, ...]] = {
    "NAMEL3SS_OPENAI_API_KEY": ("OPENAI_API_KEY",),
    "NAMEL3SS_ANTHROPIC_API_KEY": ("ANTHROPIC_API_KEY",),
    "NAMEL3SS_GEMINI_API_KEY": ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
    "NAMEL3SS_MISTRAL_API_KEY": ("MISTRAL_API_KEY",),
}


def discover_required_secrets(
    program: ir.Program | None,
    config: AppConfig,
    *,
    target: str,
    app_path: Path | None,
) -> list[SecretRef]:
    dotenv_values = _load_dotenv(app_path)
    required = _required_secret_names(program, config)
    return [_secret_ref(name, dotenv_values, target=target) for name in sorted(required)]


def discover_required_secrets_for_profiles(
    ai_profiles: dict[str, ir.AIDecl] | None,
    config: AppConfig,
    *,
    target: str,
    app_path: Path | None,
) -> list[SecretRef]:
    dotenv_values = _load_dotenv(app_path)
    providers = _providers_from_profiles(ai_profiles or {})
    required = _required_secret_names_for_providers(providers, config)
    return [_secret_ref(name, dotenv_values, target=target) for name in sorted(required)]


def _required_secret_names(program: ir.Program | None, config: AppConfig) -> set[str]:
    providers = _providers_from_program(program)
    names = _required_secret_names_for_providers(providers, config)
    names.update(_secret_names_from_program(program))
    return names


def _required_secret_names_for_providers(providers: Iterable[str], config: AppConfig) -> set[str]:
    names: set[str] = set()
    for provider in providers:
        normalized = (provider or "").lower()
        if normalized in PROVIDER_ENV:
            names.add(PROVIDER_ENV[normalized])
    target = (config.persistence.target or "memory").lower()
    if target == "postgres":
        names.add("N3_DATABASE_URL")
    if target == "edge":
        names.add("N3_EDGE_KV_URL")
    return names


def _providers_from_program(program: ir.Program | None) -> list[str]:
    if program is None:
        return []
    return _providers_from_profiles(getattr(program, "ais", {}) or {})


def _secret_names_from_program(program: ir.Program | None) -> set[str]:
    if program is None:
        return set()
    names: set[str] = set()
    for flow in program.flows:
        names.update(_secret_names_from_statements(flow.body))
    for job in program.jobs:
        names.update(_secret_names_from_statements(job.body))
        if job.when is not None:
            names.update(_secret_names_from_expr(job.when))
    for func in program.functions.values():
        names.update(_secret_names_from_statements(func.body))
    return names


def _secret_names_from_statements(statements: list[ir.Statement]) -> set[str]:
    names: set[str] = set()
    for stmt in statements:
        names.update(_secret_names_from_statement(stmt))
    return names


def _secret_names_from_statement(stmt: ir.Statement) -> set[str]:
    if isinstance(stmt, (ir.Let, ir.Set)):
        return _secret_names_from_expr(stmt.expression)
    if isinstance(stmt, ir.If):
        names = _secret_names_from_expr(stmt.condition)
        names.update(_secret_names_from_statements(stmt.then_body))
        names.update(_secret_names_from_statements(stmt.else_body))
        return names
    if isinstance(stmt, ir.Return):
        return _secret_names_from_expr(stmt.expression)
    if isinstance(stmt, ir.Repeat):
        names = _secret_names_from_expr(stmt.count)
        names.update(_secret_names_from_statements(stmt.body))
        return names
    if isinstance(stmt, ir.RepeatWhile):
        names = _secret_names_from_expr(stmt.condition)
        names.update(_secret_names_from_statements(stmt.body))
        return names
    if isinstance(stmt, ir.ForEach):
        names = _secret_names_from_expr(stmt.iterable)
        names.update(_secret_names_from_statements(stmt.body))
        return names
    if isinstance(stmt, ir.Match):
        names = _secret_names_from_expr(stmt.expression)
        for case in stmt.cases:
            names.update(_secret_names_from_expr(case.pattern))
            names.update(_secret_names_from_statements(case.body))
        if stmt.otherwise:
            names.update(_secret_names_from_statements(stmt.otherwise))
        return names
    if isinstance(stmt, ir.TryCatch):
        names = _secret_names_from_statements(stmt.try_body)
        names.update(_secret_names_from_statements(stmt.catch_body))
        return names
    if isinstance(stmt, ir.AskAIStmt):
        return _secret_names_from_expr(stmt.input_expr)
    if isinstance(stmt, ir.RunAgentStmt):
        return _secret_names_from_expr(stmt.input_expr)
    if isinstance(stmt, ir.RunAgentsParallelStmt):
        names: set[str] = set()
        for entry in stmt.entries:
            names.update(_secret_names_from_expr(entry.input_expr))
        return names
    if isinstance(stmt, ir.ParallelBlock):
        names: set[str] = set()
        for task in stmt.tasks:
            names.update(_secret_names_from_statements(task.body))
        return names
    if isinstance(stmt, ir.Create):
        return _secret_names_from_expr(stmt.values)
    if isinstance(stmt, ir.Find):
        return _secret_names_from_expr(stmt.predicate)
    if isinstance(stmt, ir.Update):
        names = _secret_names_from_expr(stmt.predicate)
        for update in stmt.updates:
            names.update(_secret_names_from_expr(update.expression))
        return names
    if isinstance(stmt, ir.Delete):
        return _secret_names_from_expr(stmt.predicate)
    if isinstance(stmt, ir.EnqueueJob):
        names: set[str] = set()
        if stmt.input_expr is not None:
            names.update(_secret_names_from_expr(stmt.input_expr))
        if stmt.schedule_expr is not None:
            names.update(_secret_names_from_expr(stmt.schedule_expr))
        return names
    if isinstance(stmt, ir.AdvanceTime):
        return _secret_names_from_expr(stmt.amount)
    if isinstance(stmt, ir.LogStmt):
        names = _secret_names_from_expr(stmt.message)
        if stmt.fields is not None:
            names.update(_secret_names_from_expr(stmt.fields))
        return names
    if isinstance(stmt, ir.MetricStmt):
        names: set[str] = set()
        if stmt.value is not None:
            names.update(_secret_names_from_expr(stmt.value))
        if stmt.labels is not None:
            names.update(_secret_names_from_expr(stmt.labels))
        return names
    return set()


def _secret_names_from_expr(expr: ir.Expression) -> set[str]:
    if isinstance(expr, ir.BuiltinCallExpr):
        names: set[str] = set()
        if expr.name == "secret" and len(expr.arguments) == 1:
            arg = expr.arguments[0]
            if isinstance(arg, ir.Literal) and isinstance(arg.value, str):
                normalized = normalize_secret_name(arg.value)
                if normalized:
                    names.add(normalized)
        for arg in expr.arguments:
            names.update(_secret_names_from_expr(arg))
        return names
    if isinstance(expr, ir.ToolCallExpr):
        names: set[str] = set()
        for arg in expr.arguments:
            names.update(_secret_names_from_expr(arg.value))
        return names
    if isinstance(expr, ir.CallFunctionExpr):
        names: set[str] = set()
        for arg in expr.arguments:
            names.update(_secret_names_from_expr(arg.value))
        return names
    if isinstance(expr, ir.UnaryOp):
        return _secret_names_from_expr(expr.operand)
    if isinstance(expr, ir.BinaryOp):
        names = _secret_names_from_expr(expr.left)
        names.update(_secret_names_from_expr(expr.right))
        return names
    if isinstance(expr, ir.Comparison):
        names = _secret_names_from_expr(expr.left)
        names.update(_secret_names_from_expr(expr.right))
        return names
    if isinstance(expr, ir.ListExpr):
        names: set[str] = set()
        for item in expr.items:
            names.update(_secret_names_from_expr(item))
        return names
    if isinstance(expr, ir.MapExpr):
        names: set[str] = set()
        for entry in expr.entries:
            names.update(_secret_names_from_expr(entry.key))
            names.update(_secret_names_from_expr(entry.value))
        return names
    if isinstance(expr, ir.ListOpExpr):
        names = _secret_names_from_expr(expr.target)
        if expr.value is not None:
            names.update(_secret_names_from_expr(expr.value))
        if expr.index is not None:
            names.update(_secret_names_from_expr(expr.index))
        return names
    if isinstance(expr, ir.MapOpExpr):
        names = _secret_names_from_expr(expr.target)
        if expr.key is not None:
            names.update(_secret_names_from_expr(expr.key))
        if expr.value is not None:
            names.update(_secret_names_from_expr(expr.value))
        return names
    if isinstance(expr, ir.ListMapExpr):
        names = _secret_names_from_expr(expr.target)
        names.update(_secret_names_from_expr(expr.body))
        return names
    if isinstance(expr, ir.ListFilterExpr):
        names = _secret_names_from_expr(expr.target)
        names.update(_secret_names_from_expr(expr.predicate))
        return names
    if isinstance(expr, ir.ListReduceExpr):
        names = _secret_names_from_expr(expr.target)
        names.update(_secret_names_from_expr(expr.start))
        names.update(_secret_names_from_expr(expr.body))
        return names
    return set()


def _providers_from_profiles(ai_profiles: dict[str, ir.AIDecl]) -> list[str]:
    providers: list[str] = []
    for ai in ai_profiles.values():
        provider = (getattr(ai, "provider", "") or "").lower()
        if provider:
            providers.append(provider)
    return providers


def _secret_ref(name: str, dotenv_values: dict[str, str], *, target: str) -> SecretRef:
    source = "missing"
    available = False
    aliases = _ENV_ALIASES.get(name, ())
    if name in dotenv_values or any(alias in dotenv_values for alias in aliases):
        source = "dotenv"
        available = True
    env_keys = _env_keys()
    if name in env_keys or any(alias in env_keys for alias in aliases):
        source = "env"
        available = True
    return SecretRef(name=name, source=source, target=target, available=available)


def _env_keys() -> set[str]:
    import os

    return set(os.environ.keys())


def _load_dotenv(app_path: Path | None) -> dict[str, str]:
    if app_path is None:
        return {}
    return load_dotenv_for_path(app_path.as_posix())


__all__ = ["discover_required_secrets", "discover_required_secrets_for_profiles", "PROVIDER_ENV"]
