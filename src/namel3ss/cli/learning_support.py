from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from namel3ss.cli.proofs import load_active_proof
from namel3ss.cli.promotion_state import load_state
from namel3ss.cli.targets import parse_target
from namel3ss.config.loader import load_config
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ir import nodes as ir
from namel3ss.module_loader import load_project


@dataclass(frozen=True)
class LearningContext:
    app_path: Path
    project_root: Path
    program: ir.Program
    modules: dict
    graph: object
    engine_target: str
    proof_id: str | None
    verify_status: str | None
    persistence: dict


def build_learning_context(app_path: Path) -> LearningContext:
    project_root = app_path.parent
    project = load_project(app_path)
    config = load_config(app_path=app_path, root=project_root)
    active = load_active_proof(project_root)
    proof_id = active.get("proof_id") if isinstance(active, dict) else None
    engine_target = _resolve_target(project_root, active if isinstance(active, dict) else {})
    verify_status = _load_verify_status(project_root)
    persistence = _persistence_summary(config)
    return LearningContext(
        app_path=app_path,
        project_root=project_root,
        program=project.program,
        modules=project.modules,
        graph=project.graph,
        engine_target=engine_target,
        proof_id=proof_id,
        verify_status=verify_status,
        persistence=persistence,
    )


def collect_capsules(project_root: Path, modules: dict) -> list[dict]:
    capsules: list[dict] = []
    for name, info in modules.items():
        source = _capsule_source(project_root, Path(info.path))
        capsules.append({"name": name, "source": source})
    return sorted(capsules, key=lambda item: item["name"])


def collect_requires(program: ir.Program) -> list[dict]:
    rules: list[dict] = []
    for flow in program.flows:
        if flow.requires:
            rules.append({"scope": "flow", "name": flow.name, "rule": render_expression(flow.requires)})
    for page in program.pages:
        if page.requires:
            rules.append({"scope": "page", "name": page.name, "rule": render_expression(page.requires)})
    return sorted(rules, key=lambda item: (item["scope"], item["name"]))


def render_expression(expr: ir.Expression) -> str:
    if isinstance(expr, ir.Literal):
        if isinstance(expr.value, str):
            return json.dumps(expr.value)
        return str(expr.value)
    if isinstance(expr, ir.VarReference):
        return expr.name
    if isinstance(expr, ir.AttrAccess):
        attrs = ".".join(expr.attrs)
        return f"{expr.base}.{attrs}" if attrs else expr.base
    if isinstance(expr, ir.StatePath):
        return "state." + ".".join(expr.path)
    if isinstance(expr, ir.UnaryOp):
        return f"{expr.op} {render_expression(expr.operand)}"
    if isinstance(expr, ir.Comparison):
        left = render_expression(expr.left)
        right = render_expression(expr.right)
        op = {
            "eq": "is",
            "ne": "is not",
            "gt": ">",
            "lt": "<",
            "gte": ">=",
            "lte": "<=",
        }.get(expr.kind, expr.kind)
        return f"{left} {op} {right}"
    if isinstance(expr, ir.BinaryOp):
        left = render_expression(expr.left)
        right = render_expression(expr.right)
        return f"{left} {expr.op} {right}"
    return "<expression>"


def summarize_pages(program: ir.Program) -> list[str]:
    return sorted(page.name for page in program.pages)


def summarize_flows(program: ir.Program) -> list[str]:
    return sorted(flow.name for flow in program.flows)


def summarize_records(program: ir.Program) -> list[str]:
    return sorted(record.name for record in program.records)


def summarize_graph(graph) -> list[str]:
    edges_by_src: dict[str, list[str]] = {}
    for src, dst in getattr(graph, "edges", []):
        edges_by_src.setdefault(src, []).append(dst)
    lines: list[str] = []
    for node in sorted(getattr(graph, "nodes", [])):
        deps = sorted(edges_by_src.get(node, []))
        if deps:
            lines.append(f"{node} -> {', '.join(deps)}")
        else:
            lines.append(node)
    return lines


def _capsule_source(project_root: Path, module_path: Path) -> str:
    try:
        rel = module_path.resolve().relative_to(project_root.resolve())
    except ValueError:
        return "unknown"
    if "packages" in rel.parts:
        return "package"
    return "local"


def _resolve_target(project_root: Path, active: dict) -> str:
    if active.get("target"):
        return str(active.get("target"))
    promotion = load_state(project_root)
    slot = promotion.get("active") or {}
    if slot.get("target"):
        return str(slot.get("target"))
    return parse_target(None).name


def _load_verify_status(project_root: Path) -> str | None:
    verify_path = project_root / ".namel3ss" / "verify.json"
    if not verify_path.exists():
        return None
    try:
        data = json.loads(verify_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return "unknown"
    if not isinstance(data, dict):
        return "unknown"
    status = data.get("status")
    return str(status) if status else "unknown"


def _persistence_summary(config) -> dict:
    target = (config.persistence.target or "memory").lower()
    descriptor = None
    if target == "sqlite":
        descriptor = config.persistence.db_path
    elif target == "postgres":
        descriptor = "postgres url set" if config.persistence.database_url else "postgres url missing"
    elif target == "edge":
        descriptor = "edge url set" if config.persistence.edge_kv_url else "edge url missing"
    elif target == "memory":
        descriptor = "memory"
    return {"target": target, "descriptor": descriptor}


def require_app_path(app_path: Path) -> None:
    if not app_path.exists():
        raise Namel3ssError(
            build_guidance_message(
                what="app.ai was not found.",
                why=f"Expected {app_path.as_posix()} to exist.",
                fix="Provide the correct app.ai path.",
                example="n3 explain app.ai",
            )
        )


__all__ = [
    "LearningContext",
    "build_learning_context",
    "collect_capsules",
    "collect_requires",
    "render_expression",
    "require_app_path",
    "summarize_flows",
    "summarize_graph",
    "summarize_pages",
    "summarize_records",
]
