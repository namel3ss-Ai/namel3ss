from __future__ import annotations

import hashlib
import shutil
import tempfile
from pathlib import Path
from typing import Any, Iterable

from namel3ss.config.loader import load_config
from namel3ss.determinism import canonicalize_run_payload, trace_hash
from namel3ss.evals.model import (
    EVAL_SCHEMA_VERSION,
    EvalCase,
    EvalCaseResult,
    EvalReport,
    EvalSuite,
    MockProviderSpec,
)
from namel3ss.evals.thresholds import evaluate_thresholds
from namel3ss.module_loader import load_project
from namel3ss.runtime.ai.provider import AIResponse, AIToolCallResponse
from namel3ss.runtime.ai.providers.mock import MockProvider
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.payload import build_error_from_exception, build_error_payload
from namel3ss.production_contract import build_run_payload
from namel3ss.runtime.executor.api import execute_program_flow
from namel3ss.runtime.memory.api import MemoryManager
from namel3ss.runtime.run_pipeline import collect_ai_outputs, finalize_run_payload, unwrap_ai_outputs
from namel3ss.runtime.store.memory_store import MemoryStore
from namel3ss.secrets import collect_secret_values
from namel3ss.utils.json_tools import dumps
from namel3ss.version import get_version


IGNORE_COPY = {".git", ".namel3ss", "__pycache__", ".pytest_cache"}


def run_eval_suite(suite: EvalSuite, *, fast: bool = False) -> EvalReport:
    cases = _select_cases(suite.cases, fast=fast)
    results = [_run_case(case, suite.path.parent) for case in cases]
    summary = _build_summary(cases, results)
    checks = evaluate_thresholds(summary, suite.thresholds)
    status = "pass" if all(check["status"] == "pass" for check in checks) else "fail"
    summary["status"] = status
    return EvalReport(
        schema_version=EVAL_SCHEMA_VERSION,
        namel3ss_version=get_version(),
        status=status,
        summary=summary,
        thresholds=checks,
        cases=tuple(results),
    )


def render_eval_text(report: EvalReport) -> str:
    summary = report.summary
    lines = [
        f"Eval: {summary.get('status', report.status).upper()}",
        f"Cases: {summary.get('passed', 0)} passed, {summary.get('failed', 0)} failed, {summary.get('cases', 0)} total",
        f"Success rate: {summary.get('success_rate', 0):.2f}",
    ]
    tool_accuracy = summary.get("tool_accuracy")
    if tool_accuracy is not None:
        lines.append(f"Tool accuracy: {tool_accuracy:.2f}")
    lines.append(f"AI calls: {summary.get('ai_calls', 0)}")
    lines.append(f"Tool calls: {summary.get('tool_calls', 0)}")
    lines.append(f"Policy violations: {summary.get('policy_violations', 0)}")
    lines.append("Case results:")
    for case in report.cases:
        lines.append(f"- {case.case_id}: {case.status}")
    return "\n".join(lines)


def _select_cases(cases: Iterable[EvalCase], *, fast: bool) -> list[EvalCase]:
    selected = [case for case in cases if not fast or "fast" in case.tags]
    if not selected:
        raise Namel3ssError("No eval cases matched the selection.")
    return selected


def _run_case(case: EvalCase, suite_root: Path) -> EvalCaseResult:
    with _workspace(case, suite_root) as workspace:
        app_path = workspace / case.app
        project = load_project(app_path)
        program = project.program
        source_text = project.sources.get(app_path)
        project_root = Path(getattr(program, "project_root", app_path.parent))
        config = load_config(app_path=app_path, root=project_root)
        secret_values = collect_secret_values(config)
        provider = _build_mock_provider(case.mock)
        memory_manager = MemoryManager(project_root=str(project_root), app_path=str(app_path))
        payload = _build_flow_payload(
            program=program,
            flow_name=case.flow,
            state=case.state,
            input_data=case.input,
            store=MemoryStore(),
            memory_manager=memory_manager,
            runtime_theme=getattr(program, "theme", None),
            config=config,
            identity=case.identity,
            source=source_text,
            project_root=project_root,
            ai_provider=provider,
        )
        payload = finalize_run_payload(payload, secret_values)
    canonical = canonicalize_run_payload(payload)
    traces = canonical.get("traces") if isinstance(canonical, dict) else []
    trace_hash_value = trace_hash(traces if isinstance(traces, list) else [])
    result_hash = _hash_value(canonical.get("result") if isinstance(canonical, dict) else None)
    tool_calls, tool_blocks = _collect_tool_events(traces if isinstance(traces, list) else [])
    ai_calls = _count_ai_calls(traces if isinstance(traces, list) else [])
    policy_violations = _count_policy_violations(traces if isinstance(traces, list) else [], tool_blocks)
    error_info = _extract_error_info(canonical)
    status, error = _evaluate_expectations(case, canonical, error_info, tool_calls, tool_blocks, trace_hash_value)
    return EvalCaseResult(
        case_id=case.case_id,
        app=case.app,
        flow=case.flow,
        status=status,
        duration_ms=0,
        ai_calls=ai_calls,
        result_hash=result_hash,
        trace_hash=trace_hash_value,
        tool_calls=tuple(tool_calls),
        tool_blocks=tuple(tool_blocks),
        policy_violations=policy_violations,
        error=error,
    )


def _workspace(case: EvalCase, suite_root: Path):
    source_app = (suite_root / case.app).resolve()
    if not source_app.exists():
        raise Namel3ssError(f"Eval app not found: {source_app.as_posix()}")
    source_root = suite_root.resolve()
    temp_dir = tempfile.TemporaryDirectory(prefix="namel3ss-eval-")
    dest_root = Path(temp_dir.name)
    _copy_project(source_root, dest_root)
    app_rel = Path(case.app)
    dest_app_root = dest_root / app_rel.parent
    _copy_tool_bindings(source_app.parent, dest_app_root)
    if case.tool_bindings is not None:
        _write_tool_bindings(dest_app_root, case.tool_bindings)
    if case.memory_packs is not None:
        _write_memory_packs_config(dest_app_root, case.memory_packs)
    return _Workspace(dest_root, temp_dir)


def _copy_project(source_root: Path, dest_root: Path) -> None:
    shutil.copytree(source_root, dest_root, dirs_exist_ok=True, ignore=_copy_ignore)


def _copy_ignore(_root: str, names: list[str]) -> set[str]:
    return {name for name in names if name in IGNORE_COPY}


def _copy_tool_bindings(source_root: Path, dest_root: Path) -> None:
    src = source_root / ".namel3ss" / "tools.yaml"
    if not src.exists():
        return
    dest = dest_root / ".namel3ss" / "tools.yaml"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")


def _write_tool_bindings(dest_root: Path, bindings: dict[str, dict[str, Any]]) -> None:
    from namel3ss.runtime.tools.bindings_yaml import ToolBinding, render_bindings_yaml

    resolved: dict[str, ToolBinding] = {}
    for tool_name, payload in bindings.items():
        if not isinstance(tool_name, str) or not isinstance(payload, dict):
            continue
        kind = payload.get("kind")
        entry = payload.get("entry")
        if not isinstance(kind, str) or not isinstance(entry, str):
            continue
        resolved[tool_name] = ToolBinding(
            kind=kind,
            entry=entry,
            runner=_optional_str(payload.get("runner")),
            url=_optional_str(payload.get("url")),
            image=_optional_str(payload.get("image")),
            command=_optional_list(payload.get("command")),
            env=_optional_str_map(payload.get("env")),
            purity=_optional_str(payload.get("purity")),
            timeout_ms=_optional_int(payload.get("timeout_ms")),
            sandbox=_optional_bool(payload.get("sandbox")),
            enforcement=_optional_str(payload.get("enforcement")),
        )
    if not resolved:
        return
    dest = dest_root / ".namel3ss" / "tools.yaml"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(render_bindings_yaml(resolved), encoding="utf-8")


def _write_memory_packs_config(dest_root: Path, packs) -> None:
    lines = ["[memory_packs]"]
    if packs.default_pack is not None:
        lines.append(f'default_pack = "{packs.default_pack}"')
    if packs.agent_overrides:
        items = ", ".join(
            f'"{key}" = "{packs.agent_overrides[key]}"' for key in sorted(packs.agent_overrides)
        )
        lines.append(f"agent_overrides = {{{items}}}")
    dest = dest_root / "namel3ss.toml"
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _build_mock_provider(spec: MockProviderSpec | None) -> MockProvider:
    if spec is None:
        return MockProvider()
    sequence: list[object] = []
    for call in spec.tool_calls:
        sequence.append(AIToolCallResponse(tool_name=call.tool_name, args=call.args))
    if spec.response is not None:
        sequence.append(AIResponse(output=spec.response))
    return MockProvider(tool_call_sequence=sequence)


def _build_flow_payload(
    *,
    program,
    flow_name: str,
    state: dict[str, Any],
    input_data: dict[str, Any],
    store: MemoryStore,
    memory_manager: MemoryManager,
    runtime_theme: str | None,
    config,
    identity: dict[str, Any] | None,
    source: str | None,
    project_root: Path,
    ai_provider: MockProvider,
) -> dict[str, Any]:
    try:
        result = execute_program_flow(
            program,
            flow_name,
            state=state,
            input=input_data,
            store=store,
            ai_provider=ai_provider,
            memory_manager=memory_manager,
            runtime_theme=runtime_theme,
            config=config,
            identity=identity,
        )
    except Exception as err:
        error_payload = _build_error_payload(err, source)
        return build_run_payload(
            ok=False,
            flow_name=flow_name,
            state=state,
            result=None,
            traces=[],
            project_root=project_root,
            error=err,
            error_payload=error_payload,
        )
    traces = [_trace_to_dict(trace) for trace in result.traces]
    ai_outputs = collect_ai_outputs(traces)
    return build_run_payload(
        ok=True,
        flow_name=flow_name,
        state=unwrap_ai_outputs(result.state, ai_outputs),
        result=unwrap_ai_outputs(result.last_value, ai_outputs),
        traces=traces,
        project_root=project_root,
    )


def _build_error_payload(error: Exception, source: str | None) -> dict[str, Any]:
    if isinstance(error, Namel3ssError):
        return build_error_from_exception(error, kind="runtime", source=source)
    return build_error_payload(str(error), kind="runtime")


def _trace_to_dict(trace: object) -> dict[str, Any]:
    if hasattr(trace, "__dict__"):
        data = getattr(trace, "__dict__")
        if isinstance(data, dict):
            return dict(data)
    if isinstance(trace, dict):
        return dict(trace)
    return {"trace": trace}


def _extract_error_info(payload: dict[str, Any]) -> dict[str, Any] | None:
    error_id = payload.get("error_id")
    error_message = payload.get("error_message")
    if error_id is None and error_message is None:
        return None
    info: dict[str, Any] = {}
    if error_id is not None:
        info["id"] = error_id
    if error_message is not None:
        info["message"] = error_message
    return info


def _evaluate_expectations(
    case: EvalCase,
    payload: dict[str, Any],
    error_info: dict[str, Any] | None,
    tool_calls: list[str],
    tool_blocks: list[str],
    trace_hash_value: str,
) -> tuple[str, dict[str, Any] | None]:
    expect = case.expect
    has_error = error_info is not None
    if expect.ok and has_error:
        return "fail", {"kind": "unexpected_error", **(error_info or {})}
    if not expect.ok and not has_error:
        return "fail", {"kind": "missing_error"}
    if expect.error_contains:
        message = (error_info or {}).get("message", "")
        if expect.error_contains not in str(message):
            return "fail", {"kind": "error_mismatch", "expected": expect.error_contains}
    if expect.result is not None:
        expected_value = _canonical_value(expect.result)
        actual_value = _canonical_value(payload.get("result"))
        if expected_value != actual_value:
            return "fail", {"kind": "result_mismatch"}
    if expect.tool_calls is not None:
        if list(expect.tool_calls) != tool_calls:
            return "fail", {"kind": "tool_calls_mismatch", "expected": list(expect.tool_calls)}
    if expect.tool_blocks is not None:
        if list(expect.tool_blocks) != tool_blocks:
            return "fail", {"kind": "tool_blocks_mismatch", "expected": list(expect.tool_blocks)}
    if expect.trace_hash is not None and expect.trace_hash != trace_hash_value:
        return "fail", {"kind": "trace_hash_mismatch", "expected": expect.trace_hash}
    return "pass", error_info


def _build_summary(cases: list[EvalCase], results: list[EvalCaseResult]) -> dict[str, Any]:
    total = len(results)
    passed = sum(1 for case in results if case.status == "pass")
    failed = total - passed
    ai_calls = sum(case.ai_calls for case in results)
    tool_cases = 0
    tool_matches = 0
    for case, result in zip(cases, results, strict=False):
        expects_tools = case.expect.tool_calls is not None or case.expect.tool_blocks is not None
        if not expects_tools:
            continue
        tool_cases += 1
        if result.status == "pass":
            tool_matches += 1
    tool_accuracy = (tool_matches / tool_cases) if tool_cases else None
    policy_violations = sum(case.policy_violations for case in results)
    success_rate = passed / total if total else 0.0
    return {
        "cases": total,
        "passed": passed,
        "failed": failed,
        "success_rate": round(success_rate, 4),
        "tool_accuracy": None if tool_accuracy is None else round(tool_accuracy, 4),
        "ai_calls": ai_calls,
        "tool_calls": sum(len(case.tool_calls) for case in results),
        "policy_violations": policy_violations,
    }


def _collect_tool_events(traces: list[dict]) -> tuple[list[str], list[str]]:
    tool_calls: list[str] = []
    tool_blocks: list[str] = []
    for trace in traces:
        if not isinstance(trace, dict):
            continue
        trace_type = trace.get("type")
        if trace_type == "tool_call" and not (trace.get("ai_name") or trace.get("agent_name")):
            tool_name = trace.get("tool_name") or trace.get("tool")
            if isinstance(tool_name, str):
                tool_calls.append(tool_name)
            if trace.get("decision") == "blocked":
                tool_blocks.append(tool_name)
        events = trace.get("canonical_events")
        if isinstance(events, list):
            for event in events:
                if not isinstance(event, dict):
                    continue
                event_type = event.get("type")
                tool_name = event.get("tool_name")
                if event_type == "tool_call_proposed" and isinstance(tool_name, str):
                    tool_calls.append(tool_name)
                if event_type == "tool_call_blocked" and isinstance(tool_name, str):
                    tool_blocks.append(tool_name)
    return tool_calls, tool_blocks


def _count_policy_violations(traces: list[dict], tool_blocks: list[str]) -> int:
    violations = len(tool_blocks)
    for trace in traces:
        if not isinstance(trace, dict):
            continue
        if trace.get("type") == "capability_check" and trace.get("allowed") is False:
            violations += 1
    return violations


def _count_ai_calls(traces: list[dict]) -> int:
    return sum(1 for trace in traces if isinstance(trace, dict) and trace.get("type") == "ai_call")


def _hash_value(value: Any) -> str | None:
    canonical = _canonical_value(value)
    if canonical is None:
        return None
    payload = dumps(canonical, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _canonical_value(value: Any) -> Any:
    payload = canonicalize_run_payload({"result": value})
    if not isinstance(payload, dict):
        return value
    return payload.get("result")


def _optional_str(value: object) -> str | None:
    if isinstance(value, str):
        return value
    return None


def _optional_list(value: object) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return list(value)
    return None


def _optional_str_map(value: object) -> dict[str, str] | None:
    if value is None:
        return None
    if isinstance(value, dict) and all(isinstance(k, str) and isinstance(v, str) for k, v in value.items()):
        return dict(value)
    return None


def _optional_int(value: object) -> int | None:
    if isinstance(value, int):
        return value
    return None


def _optional_bool(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    return None


class _Workspace:
    def __init__(self, root: Path, temp_dir: tempfile.TemporaryDirectory):
        self.root = root
        self._temp_dir = temp_dir

    def __enter__(self) -> Path:
        return self.root

    def __exit__(self, exc_type, exc, tb) -> None:
        self._temp_dir.cleanup()


__all__ = ["run_eval_suite", "render_eval_text"]
