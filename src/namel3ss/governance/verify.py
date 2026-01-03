from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Iterable
from urllib.request import urlopen

from namel3ss.cli.builds import load_build_metadata, read_latest_build_id
from namel3ss.cli.targets import parse_target
from namel3ss.config.loader import load_config
from namel3ss.errors.base import Namel3ssError
from namel3ss.governance.verify_capabilities import check_pack_capabilities, check_tool_guarantees
from namel3ss.governance.verify_types import VerifyCheck, check_to_dict
from namel3ss.ir import nodes as ir
from namel3ss.module_loader import load_project
from namel3ss.pkg.lockfile import LOCKFILE_FILENAME, read_lockfile
from namel3ss.pkg.verify import verify_installation
from namel3ss.proofs import build_engine_proof
from namel3ss.runtime.service_runner import ServiceRunner
from namel3ss.secrets import collect_secret_values


VERIFY_SCHEMA_VERSION = 1


def run_verify(
    app_path: Path,
    *,
    target: str,
    prod: bool,
    allow_unsafe: bool = False,
    config_root: Path | None = None,
    project_root_override: Path | None = None,
) -> dict:
    project = load_project(app_path)
    project_root = project_root_override or project.app_path.parent
    config = load_config(app_path=project.app_path, root=config_root or project_root)
    secret_values = collect_secret_values(config)
    checks = [
        _check_secrets_redaction(app_path, project_root, target, secret_values),
        _check_access_control(project.program, prod),
        _check_audit_policy(project.program, prod),
        _check_package_integrity(project_root),
        check_pack_capabilities(project_root, config, prod),
        check_tool_guarantees(project_root, config, project.program.tools, prod, allow_unsafe=allow_unsafe),
        _check_engine_readiness(app_path, target, config, prod),
        _check_determinism(project_root, target, prod),
    ]
    statuses = [check.status for check in checks]
    status = "fail" if "fail" in statuses or (prod and "warn" in statuses) else "ok"
    payload = {
        "schema_version": VERIFY_SCHEMA_VERSION,
        "status": status,
        "engine_target": parse_target(target).name,
        "checks": [check_to_dict(check) for check in checks],
    }
    return payload


def _check_secrets_redaction(
    app_path: Path,
    project_root: Path,
    target: str,
    secret_values: list[str],
) -> VerifyCheck:
    if not secret_values:
        return VerifyCheck(
            id="secrets_redaction",
            status="ok",
            message="No secrets configured; redaction not required.",
            fix="Add secrets via environment variables when needed.",
        )
    proof_id, proof = build_engine_proof(app_path, target=target)
    proof_text = json.dumps(proof, sort_keys=True)
    leaked = _find_leaks(proof_text, secret_values)
    observe_path = project_root / ".namel3ss" / "observe.jsonl"
    observe_leaks: list[str] = []
    if observe_path.exists():
        observe_text = observe_path.read_text(encoding="utf-8")
        observe_leaks = _find_leaks(observe_text, secret_values)
    if leaked or observe_leaks:
        return VerifyCheck(
            id="secrets_redaction",
            status="fail",
            message="Secret values were found in proof or observe logs.",
            fix="Rotate the secret, clear logs, and re-run with redaction enabled.",
            details={"proof_id": proof_id, "leaks": sorted(set(leaked + observe_leaks))},
        )
    return VerifyCheck(
        id="secrets_redaction",
        status="ok",
        message="No secret values found in proof or observe logs.",
        fix="None.",
    )


def _check_access_control(program: ir.Program, prod: bool) -> VerifyCheck:
    mutating_flows = [flow for flow in program.flows if _flow_mutates(flow)]
    missing_flow_requires = sorted(flow.name for flow in mutating_flows if flow.requires is None)
    pages_missing_requires = sorted(page.name for page in program.pages if _page_has_form(page) and page.requires is None)
    if not missing_flow_requires and not pages_missing_requires:
        return VerifyCheck(
            id="access_control",
            status="ok",
            message="Mutating flows and forms require access rules.",
            fix="None.",
        )
    status = "fail" if prod else "warn"
    message = "Public mutations detected."
    fix = "Add requires to mutating flows and pages with forms."
    details = {
        "flows_missing_requires": missing_flow_requires,
        "pages_missing_requires": pages_missing_requires,
    }
    return VerifyCheck(id="access_control", status=status, message=message, fix=fix, details=details)


def _check_audit_policy(program: ir.Program, prod: bool) -> VerifyCheck:
    required = os.getenv("N3_AUDIT_REQUIRED", "").strip().lower() in {"1", "true", "yes", "on"}
    if not required:
        return VerifyCheck(
            id="audit_policy",
            status="ok",
            message="Audit-required policy is disabled.",
            fix="Set N3_AUDIT_REQUIRED=1 to enforce audited mutations.",
        )
    mutating_flows = [flow for flow in program.flows if _flow_mutates(flow)]
    missing = sorted(flow.name for flow in mutating_flows if not getattr(flow, "audited", False))
    if not missing:
        return VerifyCheck(
            id="audit_policy",
            status="ok",
            message="All mutating flows are audited.",
            fix="None.",
        )
    return VerifyCheck(
        id="audit_policy",
        status="fail" if prod else "warn",
        message="Mutating flows are missing audited.",
        fix="Add audited to flows that write data.",
        details={"flows_missing_audit": missing},
    )


def _check_package_integrity(project_root: Path) -> VerifyCheck:
    try:
        lock = read_lockfile(project_root)
    except Namel3ssError as err:
        return VerifyCheck(
            id="package_integrity",
            status="fail",
            message="Lockfile is missing or invalid.",
            fix="Run `n3 pkg install` to regenerate the lockfile.",
            details={"error": str(err)},
        )
    packages_dir = project_root / "packages"
    if not _packages_required(project_root, lock) and not packages_dir.exists():
        return VerifyCheck(
            id="package_integrity",
            status="ok",
            message="Packages match the lockfile and include license metadata.",
            fix="None.",
            details={
                "skipped": True,
                "reason": "packages directory missing and packages not required",
            },
        )
    issues = verify_installation(project_root, lockfile=lock)
    missing_license = [pkg.name for pkg in lock.packages if not pkg.license_id and not pkg.license_file]
    if issues or missing_license:
        details = {
            "issues": [f"{issue.name}: {issue.message}" for issue in issues],
            "missing_license": sorted(missing_license),
        }
        return VerifyCheck(
            id="package_integrity",
            status="fail",
            message="Package integrity checks failed.",
            fix="Reinstall packages and ensure license metadata is present.",
            details=details,
        )
    return VerifyCheck(
        id="package_integrity",
        status="ok",
        message="Packages match the lockfile and include license metadata.",
        fix="None.",
    )


def _packages_required(project_root: Path, lock) -> bool:
    required = os.getenv("N3_PACKAGE_INTEGRITY_REQUIRED", "").strip().lower()
    if required in {"1", "true", "yes", "on"}:
        return True
    if getattr(lock, "packages", None):
        return len(lock.packages) > 0
    return (project_root / "packages").exists()


def _check_engine_readiness(app_path: Path, target: str, config, prod: bool) -> VerifyCheck:
    target_name = parse_target(target).name
    readiness_notes: list[str] = []
    status = "ok"
    if target_name == "service":
        ok, message = _check_service_runner(app_path, target_name)
        if not ok:
            status = "fail"
            readiness_notes.append(message)
    if target_name == "edge":
        status = "fail" if prod else "warn"
        readiness_notes.append("Edge engine is stubbed in this release.")
    persistence_target = (config.persistence.target or "memory").lower()
    if persistence_target == "postgres":
        ok, message = _check_postgres_config(config.persistence.database_url)
        if not ok:
            status = "fail"
            readiness_notes.append(message)
    if status == "ok":
        return VerifyCheck(
            id="engine_readiness",
            status="ok",
            message="Engine target readiness checks passed.",
            fix="None.",
        )
    return VerifyCheck(
        id="engine_readiness",
        status=status,
        message="; ".join(readiness_notes) if readiness_notes else "Engine readiness warnings.",
        fix="Resolve the readiness issues before production use.",
    )


def _check_determinism(project_root: Path, target: str, prod: bool) -> VerifyCheck:
    lock_path = project_root / LOCKFILE_FILENAME
    if not lock_path.exists():
        return VerifyCheck(
            id="determinism",
            status="fail",
            message="Lockfile is missing; determinism cannot be verified.",
            fix="Run `n3 pkg install` to create a lockfile.",
        )
    lock_digest = hashlib.sha256(lock_path.read_text(encoding="utf-8").encode("utf-8")).hexdigest()
    build_id = read_latest_build_id(project_root, target)
    if not build_id:
        return VerifyCheck(
            id="determinism",
            status="fail" if prod else "warn",
            message="No build snapshot found for the target.",
            fix="Run `n3 pack --target <target>` before verifying determinism.",
        )
    _, meta = load_build_metadata(project_root, target, build_id)
    if meta.get("lockfile_digest") != lock_digest:
        return VerifyCheck(
            id="determinism",
            status="fail",
            message="Build snapshot does not match the current lockfile.",
            fix="Rebuild with `n3 pack --target <target>` to align snapshots.",
            details={"build_id": build_id},
        )
    return VerifyCheck(
        id="determinism",
        status="ok",
        message="Build snapshot matches the current lockfile.",
        fix="None.",
    )


def _check_service_runner(app_path: Path, target: str) -> tuple[bool, str]:
    runner = ServiceRunner(app_path, target, build_id=None, port=0)
    try:
        runner.start(background=True)
        time.sleep(0.1)
        port = runner.bound_port
        health = _http_json(f"http://127.0.0.1:{port}/health")
        version = _http_json(f"http://127.0.0.1:{port}/version")
        if not health.get("ok") or not version.get("ok"):
            return False, "Service health/version endpoints returned non-ok responses."
        return True, "Service endpoints are ready."
    except Exception as err:
        return False, f"Service runner check failed: {err}"
    finally:
        runner.shutdown()


def _http_json(url: str) -> dict:
    with urlopen(url, timeout=3) as resp:
        data = resp.read().decode("utf-8")
    parsed = json.loads(data)
    return parsed if isinstance(parsed, dict) else {}


def _check_postgres_config(url: str | None) -> tuple[bool, str]:
    if not url:
        return False, "Postgres target missing N3_DATABASE_URL."
    from urllib.parse import urlparse

    parsed = urlparse(url)
    if parsed.scheme not in {"postgres", "postgresql"} or not parsed.hostname:
        return False, "Postgres URL is invalid or missing host."
    return True, "Postgres URL configured."


def _flow_mutates(flow: ir.Flow) -> bool:
    return _statements_mutate(flow.body)


def _statements_mutate(stmts: Iterable[ir.Statement]) -> bool:
    for stmt in stmts:
        if isinstance(stmt, (ir.Save, ir.Create)):
            return True
        if isinstance(stmt, ir.If):
            if _statements_mutate(stmt.then_body) or _statements_mutate(stmt.else_body):
                return True
        if isinstance(stmt, ir.Repeat):
            if _statements_mutate(stmt.body):
                return True
        if isinstance(stmt, ir.ForEach):
            if _statements_mutate(stmt.body):
                return True
        if isinstance(stmt, ir.TryCatch):
            if _statements_mutate(stmt.try_body) or _statements_mutate(stmt.catch_body):
                return True
        if isinstance(stmt, ir.Match):
            if any(_statements_mutate(case.body) for case in stmt.cases):
                return True
            if stmt.otherwise and _statements_mutate(stmt.otherwise):
                return True
    return False


def _page_has_form(page: ir.Page) -> bool:
    return _page_items_have_form(page.items)


def _page_items_have_form(items: Iterable[ir.PageItem]) -> bool:
    for item in items:
        if isinstance(item, ir.FormItem):
            return True
        if hasattr(item, "children"):
            children = getattr(item, "children") or []
            if _page_items_have_form(children):
                return True
    return False


def _find_leaks(text: str, secret_values: Iterable[str]) -> list[str]:
    leaks: list[str] = []
    for secret in secret_values:
        if secret and len(secret) >= 4 and secret in text:
            leaks.append(secret)
    return leaks


__all__ = ["VERIFY_SCHEMA_VERSION", "run_verify"]
