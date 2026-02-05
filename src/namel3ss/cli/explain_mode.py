from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.cli.proofs import load_active_proof, load_proof_state, proof_dir, read_proof
from namel3ss.cli.promotion_state import load_state
from namel3ss.cli.why_mode import build_why_lines, build_why_payload
from namel3ss.cli.explain_summary import (
    summarize_ai_flows,
    summarize_ai_metadata,
    summarize_capsules,
    summarize_crud,
    summarize_datasets,
    summarize_prompts,
    summarize_routes,
)
from namel3ss.config.loader import load_config
from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.module_loader import load_project
from namel3ss.observability.enablement import observability_enabled
from namel3ss.runtime.observability.collector import build_observability_payload
from namel3ss.proofs import build_engine_proof
from namel3ss.runtime.capabilities.report import collect_tool_reports
from namel3ss.runtime.audit import build_audit_report, build_decision_model, render_audit
from namel3ss.runtime.composition.explain import build_composition_explain_bundle
from namel3ss.ingestion.policy_inspection import inspect_ingestion_policy
from namel3ss.secrets import collect_secret_values
from namel3ss.utils.json_tools import dumps_pretty


@dataclass
class _ExplainParams:
    app_arg: str | None
    json_mode: bool
    mode: str
    upload_id: str | None
    query: str | None
    input_path: str | None
    include_observability: bool


def run_explain_command(args: list[str]) -> int:
    params = _parse_args(args)
    app_path = resolve_app_path(params.app_arg)
    if params.mode == "audit":
        return _run_audit(app_path, params)
    if params.mode != "default":
        payload = build_why_payload(app_path)
        if params.json_mode:
            print(dumps_pretty(payload))
            return 0
        lines = build_why_lines(payload, audience="non_technical" if params.mode == "non_technical" else "default")
        print("\n".join(lines))
        return 0
    payload = build_explain_payload(app_path, include_observability=params.include_observability)
    if params.json_mode:
        print(dumps_pretty(payload))
        return 0
    _print_human(payload)
    return 0


def _parse_args(args: list[str]) -> _ExplainParams:
    app_arg = None
    json_mode = False
    mode = "default"
    upload_id = None
    query = None
    input_path = None
    audit_requested = False
    why_requested = False
    non_technical_requested = False
    include_observability = False
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "prod":
            i += 1
            continue
        if arg == "--audit":
            audit_requested = True
            mode = "audit"
            i += 1
            continue
        if arg == "--why":
            why_requested = True
            mode = "why"
            i += 1
            continue
        if arg == "--non-technical":
            non_technical_requested = True
            mode = "non_technical"
            i += 1
            continue
        if arg == "--json":
            json_mode = True
            i += 1
            continue
        if arg == "--observability":
            include_observability = True
            i += 1
            continue
        if arg == "--input":
            if i + 1 >= len(args):
                raise Namel3ssError(
                    build_guidance_message(
                        what="--input flag is missing a value.",
                        why="Audit explain requires a JSON payload path.",
                        fix="Provide a path to a run payload JSON file.",
                        example="n3 explain --audit --input .namel3ss/run/last.json",
                    )
                )
            input_path = args[i + 1]
            i += 2
            continue
        if arg == "--upload":
            if i + 1 >= len(args):
                raise Namel3ssError(
                    build_guidance_message(
                        what="--upload flag is missing a value.",
                        why="Audit explain expects an upload id.",
                        fix="Provide the upload checksum.",
                        example="n3 explain --audit --upload <checksum>",
                    )
                )
            upload_id = args[i + 1]
            i += 2
            continue
        if arg == "--query":
            if i + 1 >= len(args):
                raise Namel3ssError(
                    build_guidance_message(
                        what="--query flag is missing a value.",
                        why="Audit explain expects a query string.",
                        fix="Provide a query to explain retrieval.",
                        example='n3 explain --audit --query "invoice"',
                    )
                )
            query = args[i + 1]
            i += 2
            continue
        if arg.startswith("--"):
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Unknown flag '{arg}'.",
                    why="Supported flags: --json, --why, --non-technical, --audit, --input, --upload, --query, --observability.",
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
    _validate_mode(
        mode,
        upload_id=upload_id,
        query=query,
        input_path=input_path,
        audit_requested=audit_requested,
        why_requested=why_requested,
        non_technical_requested=non_technical_requested,
    )
    return _ExplainParams(app_arg, json_mode, mode, upload_id, query, input_path, include_observability)


def _validate_mode(
    mode: str,
    *,
    upload_id: str | None,
    query: str | None,
    input_path: str | None,
    audit_requested: bool,
    why_requested: bool,
    non_technical_requested: bool,
) -> None:
    if audit_requested and (why_requested or non_technical_requested):
        raise Namel3ssError(
            build_guidance_message(
                what="Explain mode flags are incompatible.",
                why="--audit cannot be combined with --why or --non-technical.",
                fix="Choose either --audit or a why mode.",
                example="n3 explain --audit --json",
            )
        )
    if mode == "audit":
        return
    if upload_id or query or input_path:
        raise Namel3ssError(
            build_guidance_message(
                what="Audit flags require --audit.",
                why="--input, --upload, and --query are only valid for audit explain.",
                fix="Add --audit or remove the audit-only flags.",
                example="n3 explain --audit --input .namel3ss/run/last.json",
            )
        )
    if mode not in {"default", "why", "non_technical"}:
        raise Namel3ssError(
            build_guidance_message(
                what="Explain mode is not supported.",
                why="Supported modes are default, --why, --non-technical, and --audit.",
                fix="Choose a supported flag.",
                example="n3 explain --audit --json",
            )
        )


def build_explain_payload(app_path, *, include_observability: bool | None = None) -> dict:
    project_root = app_path.parent
    active = _hydrate_active_proof(project_root, load_active_proof(project_root))
    proof_id = active.get("proof_id") if isinstance(active, dict) else None
    proof = read_proof(project_root, proof_id) if proof_id else {}
    if not proof_id:
        target = active.get("target") if isinstance(active, dict) else None
        if not target:
            promotion = load_state(project_root)
            target = (promotion.get("active") or {}).get("target")
        target = target or "local"
        try:
            proof_id, proof = build_engine_proof(app_path, target=target)
        except Exception:
            proof_id, proof = None, {}
        if proof_id and isinstance(active, dict):
            active.setdefault("proof_id", proof_id)
            active.setdefault("target", target)
            if isinstance(proof, dict):
                active.setdefault("build_id", (proof.get("build") or {}).get("build_id"))
    return _assemble_explain_payload(app_path, active, proof, include_observability=include_observability)


def _assemble_explain_payload(
    app_path,
    active: dict,
    proof: dict,
    *,
    include_observability: bool | None,
) -> dict:
    project_root = app_path.parent
    config = load_config(app_path=app_path, root=project_root)
    project = load_project(app_path)
    secret_values = collect_secret_values(config)
    promotion = load_state(project_root)
    target = active.get("target") if isinstance(active, dict) else None
    if not target:
        target = (promotion.get("active") or {}).get("target")
    composition = build_composition_explain_bundle(
        project_root,
        app_path=app_path,
        secret_values=secret_values,
    )
    payload = {
        "schema_version": 1,
        "engine_target": target or "none",
        "active_proof_id": active.get("proof_id") if isinstance(active, dict) else None,
        "active_build_id": active.get("build_id") if isinstance(active, dict) else None,
        "persistence": proof.get("persistence")
        or {"target": config.persistence.target, "descriptor": None},
        "access_rules": proof.get("identity", {}).get("requires", {}),
        "tenant_scoping": proof.get("identity", {}).get("tenant_scoping", {}),
        "policy": inspect_ingestion_policy(
            getattr(project.program, "project_root", None),
            getattr(project.program, "app_path", None),
            policy_decl=getattr(project.program, "policy", None),
        ),
        "capsules": summarize_capsules(proof),
        "governance": proof.get("governance") or _load_governance(project_root),
        "composition": composition,
        "tools": collect_tool_reports(
            project_root,
            config,
            project.program.tools,
            pack_allowlist=getattr(project.program, "pack_allowlist", None),
        ),
        "flows": len(project.program.flows),
        "pages": len(project.program.pages),
        "records": len(project.program.records),
        "routes": summarize_routes(project.program),
        "crud": summarize_crud(project.program),
        "prompts": summarize_prompts(project.program),
        "ai_flows": summarize_ai_flows(project.program),
        "ai_metadata": summarize_ai_metadata(project.program),
        "datasets": summarize_datasets(project.program),
    }
    enabled = observability_enabled() if include_observability is None else include_observability
    if enabled:
        payload["observability"] = build_observability_payload(
            project_root,
            app_path=app_path,
            secret_values=secret_values,
        )
    return payload


def _hydrate_active_proof(project_root: Path, active: dict | None) -> dict:
    normalized = active if isinstance(active, dict) else {}
    state = load_proof_state(project_root)
    state_active = state.get("active") if isinstance(state, dict) else {}
    if isinstance(state_active, dict):
        for key in ("proof_id", "target", "build_id"):
            if not normalized.get(key) and state_active.get(key):
                normalized[key] = state_active.get(key)
    if not normalized.get("proof_id"):
        latest = _latest_proof_id(project_root)
        if latest:
            normalized["proof_id"] = latest
    return normalized


def _latest_proof_id(project_root: Path) -> str | None:
    root = proof_dir(project_root)
    if not root.exists():
        return None
    proofs = sorted(root.glob("proof-*.json"))
    if not proofs:
        return None
    return proofs[-1].stem


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


def _run_audit(app_path: Path, params: _ExplainParams) -> int:
    project_root = app_path.parent
    project = load_project(app_path)
    config = load_config(app_path=app_path, root=project_root)
    secret_values = collect_secret_values(config)
    payload = _load_audit_payload(project_root, params.input_path)
    state, traces = _extract_state_traces(payload)
    upload_id = params.upload_id or _infer_upload_id(payload)
    query = params.query if params.query is not None else _infer_query(payload)
    model = build_decision_model(
        state=state,
        traces=traces,
        project_root=project_root,
        app_path=app_path,
        policy_decl=getattr(project.program, "policy", None),
        identity=None,
        upload_id=upload_id,
        query=query,
        secret_values=secret_values,
    )
    report = build_audit_report(
        model,
        project_root=project_root,
        app_path=app_path,
        secret_values=secret_values,
    )
    if params.json_mode:
        print(canonical_json_dumps(report, pretty=True, drop_run_keys=False))
        return 0
    print(render_audit(report))
    return 0


def _load_audit_payload(project_root: Path, input_path: str | None) -> dict:
    path = Path(input_path) if input_path else project_root / ".namel3ss" / "run" / "last.json"
    if not path.exists():
        raise Namel3ssError(
            build_guidance_message(
                what="Audit input payload was not found.",
                why=f"Expected a run payload at {path}.",
                fix="Run a flow or provide --input with a JSON payload.",
                example="n3 explain --audit --input .namel3ss/run/last.json",
            )
        )
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise Namel3ssError(
            build_guidance_message(
                what="Audit input payload is not valid JSON.",
                why=str(exc),
                fix="Provide a valid JSON run payload.",
                example="n3 run app.ai --json > run.json",
            )
        ) from exc
    return data if isinstance(data, dict) else {}


def _extract_state_traces(payload: dict) -> tuple[dict, list[dict]]:
    state = payload.get("state")
    traces = payload.get("traces")
    contract = payload.get("contract") if isinstance(payload, dict) else None
    if not isinstance(state, dict) and isinstance(contract, dict):
        state = contract.get("state")
    if not isinstance(traces, list) and isinstance(contract, dict):
        traces = contract.get("traces")
    return (state if isinstance(state, dict) else {}, traces if isinstance(traces, list) else [])


def _infer_upload_id(payload: dict) -> str | None:
    result = payload.get("result")
    if not isinstance(result, dict):
        return None
    ingestion = result.get("ingestion")
    if isinstance(ingestion, dict):
        upload_id = ingestion.get("upload_id")
        return str(upload_id) if upload_id else None
    return None


def _infer_query(payload: dict) -> str | None:
    result = payload.get("result")
    if not isinstance(result, dict):
        return None
    retrieval = result.get("retrieval")
    if isinstance(retrieval, dict):
        query = retrieval.get("query")
        if isinstance(query, str):
            return query
    return None


__all__ = ["build_explain_payload", "run_explain_command"]
