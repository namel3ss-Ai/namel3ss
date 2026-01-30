from __future__ import annotations

import json
from dataclasses import dataclass

from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ir import nodes as ir
from namel3ss.ir.serialize import dump_ir
from namel3ss.runtime.executor.result import ExecutionResult
from namel3ss.runtime.native.exec_adapter import native_exec_available, native_exec_enabled, native_exec_ir
from namel3ss.runtime.native.status import NativeStatus


@dataclass(frozen=True)
class NativeExecConfig:
    flow_name: str
    runtime_theme: str | None
    theme_source: str | None


def native_exec_supported(program: ir.Program, flow: ir.Flow) -> bool:
    if getattr(flow, "audited", False):
        return False
    if getattr(flow, "declarative", False):
        return False
    if getattr(flow, "requires", None) is not None:
        return False
    if getattr(program, "records", None):
        return False
    if getattr(program, "policy", None) is not None:
        return False
    if getattr(program, "functions", None):
        return False
    if getattr(program, "jobs", None):
        return False
    for stmt in getattr(flow, "body", []) or []:
        if isinstance(stmt, ir.Set):
            if not isinstance(stmt.target, ir.StatePath):
                return False
            if not _expr_supported(stmt.expression):
                return False
            continue
        if isinstance(stmt, ir.Return):
            if not _expr_supported(stmt.expression):
                return False
            continue
        return False
    return True


def try_native_execute(
    program: ir.Program,
    flow: ir.Flow,
    config: NativeExecConfig,
) -> ExecutionResult | None:
    if not native_exec_enabled():
        return None
    if not native_exec_supported(program, flow):
        return None
    if not native_exec_available():
        return None
    payload = dump_ir(program)
    ir_bytes = canonical_json_dumps(payload, pretty=False).encode("utf-8")
    config_bytes = _config_bytes(config)
    outcome = native_exec_ir(ir_bytes, config_bytes)
    if outcome.status == NativeStatus.NOT_IMPLEMENTED:
        return None
    if outcome.status != NativeStatus.OK:
        raise Namel3ssError(_native_error_message(outcome.status))
    if not outcome.payload:
        raise Namel3ssError(_native_error_message(NativeStatus.ERROR))
    result_payload = json.loads(outcome.payload.decode("utf-8"))
    return _result_from_payload(result_payload)


def _expr_supported(expr: ir.Expression) -> bool:
    return isinstance(expr, (ir.Literal, ir.StatePath))


def _config_bytes(config: NativeExecConfig) -> bytes:
    payload = {
        "flow_name": config.flow_name,
        "runtime_theme": config.runtime_theme,
        "theme_source": config.theme_source,
    }
    return canonical_json_dumps(payload, pretty=False).encode("utf-8")


def _result_from_payload(payload: object) -> ExecutionResult:
    if not isinstance(payload, dict):
        raise Namel3ssError(_native_error_message(NativeStatus.INVALID_ARGUMENT))
    state = payload.get("state") if isinstance(payload.get("state"), dict) else {}
    result = ExecutionResult(
        state=state,
        last_value=payload.get("last_value"),
        traces=payload.get("traces") if isinstance(payload.get("traces"), list) else [],
        execution_steps=payload.get("execution_steps") if isinstance(payload.get("execution_steps"), list) else [],
        runtime_theme=payload.get("runtime_theme"),
    )
    result.theme_source = payload.get("theme_source")
    return result


def _native_error_message(status: NativeStatus) -> str:
    return build_guidance_message(
        what="Native executor failed.",
        why=f"Native executor status: {status.name}.",
        fix="Disable native execution or update the native runtime.",
        example="N3_NATIVE_EXEC=0 n3 run",
    )


__all__ = ["NativeExecConfig", "native_exec_supported", "try_native_execute"]
