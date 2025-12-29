from __future__ import annotations

import json
from pathlib import Path

from namel3ss.runtime.errors.explain.collect import collect_last_error
from namel3ss.runtime.errors.explain.link import link_error_to_artifacts
from namel3ss.runtime.errors.explain.model import ErrorState, RecoveryOption
from namel3ss.runtime.errors.explain.normalize import build_plain_text, write_last_error
from namel3ss.runtime.errors.explain.render_plain import render_fix
from namel3ss.runtime.tools.explain.decision import ToolDecision

API_VERSION = "errors.v1"


def build_error_explain_pack(project_root: Path) -> dict | None:
    packs = _load_packs(project_root)
    run_last = packs.get("run")
    if not isinstance(run_last, dict):
        return None

    error = collect_last_error(project_root)
    if error is None:
        return {
            "ok": True,
            "api_version": API_VERSION,
            "summary": "No errors in the last run.",
        }

    impact = link_error_to_artifacts(error, packs)
    options = infer_recovery_options(error, packs)
    error = _with_updates(error, impact, options)
    return {
        "ok": False,
        "api_version": API_VERSION,
        "summary": _summary_text(error),
        "error": error.as_dict(),
    }


def write_error_explain_artifacts(root: Path, pack: dict) -> str:
    text = render_fix(pack)
    plain = build_plain_text(pack)
    write_last_error(root, pack, plain, text)
    return text


def infer_recovery_options(error: ErrorState, packs: dict) -> list[RecoveryOption]:
    options: list[RecoveryOption] = []
    if error.kind == "permission" and _mentions_identity(error):
        options.append(
            RecoveryOption(
                id="provide_identity",
                title="Provide identity",
                how="Provide identity fields and run again.",
                source="inferred",
            )
        )

    tools = packs.get("tools")
    if isinstance(tools, dict):
        decisions = _decisions(tools)
        if _blocked_for_network(decisions):
            options.append(
                RecoveryOption(
                    id="request_permission",
                    title="Allow network",
                    how="Allow network for this tool or run without it.",
                    source="inferred",
                )
            )
        if _blocked_for_sandbox(decisions):
            options.append(
                RecoveryOption(
                    id="enable_sandbox",
                    title="Enable sandbox",
                    how="Enable sandbox for this tool or adjust overrides.",
                    source="inferred",
                )
            )
        if _tool_timed_out(decisions):
            options.append(
                RecoveryOption(
                    id="retry",
                    title="Retry the tool",
                    how="Try again or increase the tool timeout.",
                    source="inferred",
                )
            )

    return _unique_options(options)


def _mentions_identity(error: ErrorState) -> bool:
    details = error.details.get("error_message") if isinstance(error.details, dict) else None
    if details and "identity" in str(details).lower():
        return True
    if error.what and "identity" in error.what.lower():
        return True
    if error.why and "identity" in error.why.lower():
        return True
    return False


def _blocked_for_network(decisions: list[ToolDecision]) -> bool:
    for decision in decisions:
        if decision.status != "blocked":
            continue
        reasons = decision.permission.reasons or []
        caps = decision.permission.capabilities_used or []
        if any("network" in str(item).lower() for item in reasons + caps):
            return True
    return False


def _blocked_for_sandbox(decisions: list[ToolDecision]) -> bool:
    for decision in decisions:
        if decision.status != "blocked":
            continue
        reasons = decision.permission.reasons or []
        if any("sandbox" in str(item).lower() for item in reasons):
            return True
        if any("coverage_missing" in str(item).lower() for item in reasons):
            return True
    return False


def _tool_timed_out(decisions: list[ToolDecision]) -> bool:
    for decision in decisions:
        if decision.status not in {"error", "blocked"}:
            continue
        message = decision.effect.error_message or ""
        error_type = decision.effect.error_type or ""
        combined = f"{message} {error_type}".lower()
        if "timeout" in combined:
            return True
    return False


def _unique_options(options: list[RecoveryOption]) -> list[RecoveryOption]:
    seen: set[str] = set()
    result: list[RecoveryOption] = []
    for option in options:
        if option.id in seen:
            continue
        seen.add(option.id)
        result.append(option)
    return result


def _summary_text(error: ErrorState) -> str:
    return f"Error: {error.kind}."


def _with_updates(error: ErrorState, impact: list[str], options: list[RecoveryOption]) -> ErrorState:
    return ErrorState(
        id=error.id,
        kind=error.kind,
        where=error.where,
        what=error.what,
        why=error.why,
        details=dict(error.details),
        impact=list(impact),
        recoverable=bool(options),
        recovery_options=list(options),
    )


def _decisions(tools: dict) -> list[ToolDecision]:
    decisions = tools.get("decisions") or []
    parsed: list[ToolDecision] = []
    for entry in decisions:
        if isinstance(entry, dict):
            parsed.append(ToolDecision.from_dict(entry))
    return parsed


def _load_packs(root: Path) -> dict:
    return {
        "run": _load_json(root / ".namel3ss" / "run" / "last.json"),
        "execution": _load_json(root / ".namel3ss" / "execution" / "last.json"),
        "tools": _load_json(root / ".namel3ss" / "tools" / "last.json"),
        "flow": _load_json(root / ".namel3ss" / "flow" / "last.json"),
        "ui": _load_json(root / ".namel3ss" / "ui" / "last.json"),
        "memory": _load_json(root / ".namel3ss" / "memory" / "last.json"),
    }


def _load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


__all__ = ["API_VERSION", "build_error_explain_pack", "infer_recovery_options", "write_error_explain_artifacts"]
