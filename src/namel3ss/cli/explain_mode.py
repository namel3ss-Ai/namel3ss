from __future__ import annotations

from dataclasses import dataclass

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.cli.proofs import load_active_proof, read_proof
from namel3ss.cli.promotion_state import load_state
from namel3ss.cli.why_mode import build_why_lines, build_why_payload
from namel3ss.config.loader import load_config
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.module_loader import load_project
from namel3ss.runtime.capabilities.report import collect_tool_reports
from namel3ss.utils.json_tools import dumps_pretty


@dataclass
class _ExplainParams:
    app_arg: str | None
    json_mode: bool
    mode: str


def run_explain_command(args: list[str]) -> int:
    params = _parse_args(args)
    app_path = resolve_app_path(params.app_arg)
    if params.mode != "default":
        payload = build_why_payload(app_path)
        if params.json_mode:
            print(dumps_pretty(payload))
            return 0
        lines = build_why_lines(payload, audience="non_technical" if params.mode == "non_technical" else "default")
        print("\n".join(lines))
        return 0
    project_root = app_path.parent
    active = load_active_proof(project_root)
    proof_id = active.get("proof_id") if isinstance(active, dict) else None
    proof = read_proof(project_root, proof_id) if proof_id else {}
    payload = _build_explain_payload(app_path, active, proof)
    if params.json_mode:
        print(dumps_pretty(payload))
        return 0
    _print_human(payload)
    return 0


def _parse_args(args: list[str]) -> _ExplainParams:
    app_arg = None
    json_mode = False
    mode = "default"
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "prod":
            i += 1
            continue
        if arg == "--why":
            mode = "why"
            i += 1
            continue
        if arg == "--non-technical":
            mode = "non_technical"
            i += 1
            continue
        if arg == "--json":
            json_mode = True
            i += 1
            continue
        if arg.startswith("--"):
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Unknown flag '{arg}'.",
                    why="Supported flags: --json, --why, --non-technical.",
                    fix="Remove the unsupported flag.",
                    example="n3 explain --json",
                )
            )
        if app_arg is None:
            app_arg = arg
            i += 1
            continue
        raise Namel3ssError(
            build_guidance_message(
                what="Too many positional arguments.",
                why="Explain accepts at most one app path.",
                fix="Provide a single app.ai path or none.",
                example="n3 explain app.ai",
            )
        )
    return _ExplainParams(app_arg, json_mode, mode)


def _build_explain_payload(app_path, active: dict, proof: dict) -> dict:
    project_root = app_path.parent
    config = load_config(app_path=app_path, root=project_root)
    project = load_project(app_path)
    promotion = load_state(project_root)
    target = active.get("target") if isinstance(active, dict) else None
    if not target:
        target = (promotion.get("active") or {}).get("target")
    return {
        "schema_version": 1,
        "engine_target": target or "none",
        "active_proof_id": active.get("proof_id") if isinstance(active, dict) else None,
        "active_build_id": active.get("build_id") if isinstance(active, dict) else None,
        "persistence": proof.get("persistence")
        or {"target": config.persistence.target, "descriptor": None},
        "access_rules": proof.get("identity", {}).get("requires", {}),
        "tenant_scoping": proof.get("identity", {}).get("tenant_scoping", {}),
        "capsules": _summarize_capsules(proof),
        "governance": proof.get("governance") or _load_governance(project_root),
        "tools": collect_tool_reports(project_root, config, project.program.tools),
    }


def _summarize_capsules(proof: dict) -> list[dict]:
    capsules = proof.get("capsules", {})
    modules = capsules.get("modules", []) if isinstance(capsules, dict) else []
    summary = []
    for module in modules:
        if not isinstance(module, dict):
            continue
        source = module.get("source", {})
        entry = {
            "name": module.get("name"),
            "source": source.get("kind") if isinstance(source, dict) else None,
        }
        summary.append(entry)
    return summary


def _load_governance(project_root) -> dict:
    path = project_root / ".namel3ss" / "verify.json"
    if not path.exists():
        return {"status": "unknown", "checks": []}
    try:
        import json

        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"status": "unknown", "checks": []}
    return data if isinstance(data, dict) else {"status": "unknown", "checks": []}


def _print_human(payload: dict) -> None:
    print(f"Engine target: {payload.get('engine_target')}")
    print(f"Active proof: {payload.get('active_proof_id')}")
    print(f"Active build: {payload.get('active_build_id')}")
    access = payload.get("access_rules", {})
    flows = access.get("flows", [])
    pages = access.get("pages", [])
    print(f"Requires rules: {len(flows)} flows, {len(pages)} pages")
    tenant = payload.get("tenant_scoping", {})
    print(f"Tenant scoping: {tenant.get('count', 0)} records")
    governance = payload.get("governance", {})
    print(f"Governance: {governance.get('status', 'unknown')}")


__all__ = ["run_explain_command"]
