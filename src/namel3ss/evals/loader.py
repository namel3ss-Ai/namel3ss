from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.evals.model import (
    EVAL_SCHEMA_VERSION,
    EvalCase,
    EvalExpectations,
    EvalMemoryPacks,
    EvalSuite,
    EvalThresholds,
    MockProviderSpec,
    ToolCallSpec,
)


def load_eval_suite(path: Path) -> EvalSuite:
    suite_path = _resolve_suite_path(path)
    raw = _read_json(suite_path)
    if not isinstance(raw, dict):
        raise Namel3ssError(_suite_error(suite_path, "Suite payload must be a JSON object."))
    schema_version = raw.get("schema_version")
    if schema_version != EVAL_SCHEMA_VERSION:
        raise Namel3ssError(
            _suite_error(
                suite_path,
                f"Unsupported eval schema '{schema_version}'. Expected '{EVAL_SCHEMA_VERSION}'.",
            )
        )
    cases = _parse_cases(raw.get("cases"), suite_path)
    thresholds = _parse_thresholds(raw.get("thresholds"), suite_path)
    return EvalSuite(schema_version=schema_version, cases=tuple(cases), thresholds=thresholds, path=suite_path)


def _resolve_suite_path(path: Path) -> Path:
    if path.exists() and path.is_file():
        return path
    if path.exists() and path.is_dir():
        candidate = path / "suite.json"
        if candidate.exists():
            return candidate
        raise Namel3ssError(_suite_error(candidate, "No eval suite found. Expected suite.json."))
    raise Namel3ssError(_suite_error(path, "Eval suite path does not exist."))


def _read_json(path: Path) -> dict:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as err:
        raise Namel3ssError(_suite_error(path, f"Unable to read eval suite: {err}")) from err
    try:
        return json.loads(text)
    except json.JSONDecodeError as err:
        raise Namel3ssError(_suite_error(path, f"Eval suite JSON parse failed: {err.msg}")) from err


def _parse_cases(value: object, path: Path) -> list[EvalCase]:
    if not isinstance(value, list) or not value:
        raise Namel3ssError(_suite_error(path, "Eval suite cases must be a non-empty list."))
    cases: list[EvalCase] = []
    seen: set[str] = set()
    for entry in value:
        if not isinstance(entry, dict):
            raise Namel3ssError(_suite_error(path, "Eval case entries must be JSON objects."))
        case_id = _require_str(entry.get("id"), path, "case id")
        if case_id in seen:
            raise Namel3ssError(_suite_error(path, f"Duplicate eval case id '{case_id}'."))
        seen.add(case_id)
        app = _require_str(entry.get("app"), path, f"case '{case_id}' app")
        flow = _require_str(entry.get("flow"), path, f"case '{case_id}' flow")
        input_data = _optional_dict(entry.get("input"), path, f"case '{case_id}' input")
        state = _optional_dict(entry.get("state"), path, f"case '{case_id}' state")
        identity = _optional_dict_or_none(entry.get("identity"), path, f"case '{case_id}' identity")
        tags = _optional_str_list(entry.get("tags"), path, f"case '{case_id}' tags")
        expect = _parse_expectations(entry.get("expect"), path, case_id)
        mock = _parse_mock(entry.get("mock"), path, case_id)
        tool_bindings = _parse_tool_bindings(entry.get("tool_bindings"), path, case_id)
        memory_packs = _parse_memory_packs(entry.get("memory_packs"), path, case_id)
        cases.append(
            EvalCase(
                case_id=case_id,
                app=app,
                flow=flow,
                input=input_data,
                state=state,
                identity=identity,
                expect=expect,
                tags=tuple(tags),
                mock=mock,
                tool_bindings=tool_bindings,
                memory_packs=memory_packs,
            )
        )
    return sorted(cases, key=lambda case: case.case_id)


def _parse_expectations(value: object, path: Path, case_id: str) -> EvalExpectations:
    if value is None:
        return EvalExpectations(
            ok=True,
            result=None,
            error_contains=None,
            tool_calls=None,
            tool_blocks=None,
            trace_hash=None,
        )
    if not isinstance(value, dict):
        raise Namel3ssError(_suite_error(path, f"case '{case_id}' expect must be an object."))
    ok = value.get("ok")
    if ok is not None and not isinstance(ok, bool):
        raise Namel3ssError(_suite_error(path, f"case '{case_id}' expect.ok must be true/false."))
    result = value.get("result")
    error_contains = value.get("error_contains")
    if error_contains is not None and not isinstance(error_contains, str):
        raise Namel3ssError(
            _suite_error(path, f"case '{case_id}' expect.error_contains must be a string.")
        )
    tool_calls = _optional_str_list(value.get("tool_calls"), path, f"case '{case_id}' expect.tool_calls")
    tool_blocks = _optional_str_list(value.get("tool_blocks"), path, f"case '{case_id}' expect.tool_blocks")
    trace_hash = value.get("trace_hash")
    if trace_hash is not None and not isinstance(trace_hash, str):
        raise Namel3ssError(_suite_error(path, f"case '{case_id}' expect.trace_hash must be a string."))
    if error_contains is not None and ok is True:
        raise Namel3ssError(_suite_error(path, f"case '{case_id}' expect.ok cannot be true with error_contains."))
    if error_contains is not None and result is not None:
        raise Namel3ssError(_suite_error(path, f"case '{case_id}' expect cannot include result and error_contains."))
    if result is not None and ok is False:
        raise Namel3ssError(_suite_error(path, f"case '{case_id}' expect.ok cannot be false with result."))
    resolved_ok = ok if ok is not None else (False if error_contains else True)
    return EvalExpectations(
        ok=resolved_ok,
        result=result,
        error_contains=error_contains,
        tool_calls=tuple(tool_calls) if tool_calls else None,
        tool_blocks=tuple(tool_blocks) if tool_blocks else None,
        trace_hash=trace_hash,
    )


def _parse_mock(value: object, path: Path, case_id: str) -> MockProviderSpec | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise Namel3ssError(_suite_error(path, f"case '{case_id}' mock must be an object."))
    tool_calls_raw = value.get("tool_calls") or []
    if not isinstance(tool_calls_raw, list):
        raise Namel3ssError(_suite_error(path, f"case '{case_id}' mock.tool_calls must be a list."))
    tool_calls: list[ToolCallSpec] = []
    for entry in tool_calls_raw:
        if not isinstance(entry, dict):
            raise Namel3ssError(_suite_error(path, f"case '{case_id}' mock.tool_calls entries must be objects."))
        tool_name = _require_str(entry.get("tool_name"), path, f"case '{case_id}' mock.tool_calls tool_name")
        args = entry.get("args") or {}
        if not isinstance(args, dict):
            raise Namel3ssError(_suite_error(path, f"case '{case_id}' mock.tool_calls args must be an object."))
        tool_calls.append(ToolCallSpec(tool_name=tool_name, args=dict(args)))
    response = value.get("response")
    if response is not None and not isinstance(response, str):
        raise Namel3ssError(_suite_error(path, f"case '{case_id}' mock.response must be a string."))
    return MockProviderSpec(tool_calls=tuple(tool_calls), response=response)


def _parse_memory_packs(value: object, path: Path, case_id: str) -> EvalMemoryPacks | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise Namel3ssError(_suite_error(path, f"case '{case_id}' memory_packs must be an object."))
    default_pack = value.get("default_pack")
    if default_pack is not None and not isinstance(default_pack, str):
        raise Namel3ssError(_suite_error(path, f"case '{case_id}' memory_packs.default_pack must be a string."))
    agent_overrides = value.get("agent_overrides") or {}
    if not isinstance(agent_overrides, dict):
        raise Namel3ssError(_suite_error(path, f"case '{case_id}' memory_packs.agent_overrides must be an object."))
    overrides: dict[str, str] = {}
    for key, val in agent_overrides.items():
        if not isinstance(key, str) or not isinstance(val, str):
            raise Namel3ssError(
                _suite_error(path, f"case '{case_id}' memory_packs.agent_overrides entries must be strings.")
            )
        overrides[key] = val
    return EvalMemoryPacks(default_pack=default_pack, agent_overrides=overrides)


def _parse_tool_bindings(value: object, path: Path, case_id: str) -> dict[str, dict[str, Any]] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise Namel3ssError(_suite_error(path, f"case '{case_id}' tool_bindings must be an object."))
    bindings: dict[str, dict[str, Any]] = {}
    for tool_name, payload in value.items():
        if not isinstance(tool_name, str) or not tool_name.strip():
            raise Namel3ssError(_suite_error(path, f"case '{case_id}' tool_bindings keys must be strings."))
        if not isinstance(payload, dict):
            raise Namel3ssError(_suite_error(path, f"case '{case_id}' tool_bindings entries must be objects."))
        kind = payload.get("kind")
        entry = payload.get("entry")
        if not isinstance(kind, str) or not isinstance(entry, str):
            raise Namel3ssError(
                _suite_error(path, f"case '{case_id}' tool_bindings entries require kind and entry strings.")
            )
        _require_optional_str(payload.get("runner"), path, case_id, "runner")
        _require_optional_str(payload.get("url"), path, case_id, "url")
        _require_optional_str(payload.get("image"), path, case_id, "image")
        _require_optional_str(payload.get("purity"), path, case_id, "purity")
        _require_optional_str(payload.get("enforcement"), path, case_id, "enforcement")
        _require_optional_bool(payload.get("sandbox"), path, case_id, "sandbox")
        _require_optional_int(payload.get("timeout_ms"), path, case_id, "timeout_ms")
        _require_optional_str_list(payload.get("command"), path, case_id, "command")
        _require_optional_str_map(payload.get("env"), path, case_id, "env")
        bindings[tool_name] = dict(payload)
    return bindings


def _parse_thresholds(value: object, path: Path) -> EvalThresholds:
    if value is None:
        return EvalThresholds(success_rate=1.0, tool_accuracy=None, max_policy_violations=0)
    if not isinstance(value, dict):
        raise Namel3ssError(_suite_error(path, "thresholds must be an object."))
    success_rate = _optional_float(value.get("success_rate"), path, "thresholds.success_rate")
    tool_accuracy = _optional_float(value.get("tool_accuracy"), path, "thresholds.tool_accuracy")
    max_policy_violations = _optional_int(value.get("max_policy_violations"), path, "thresholds.max_policy_violations")
    return EvalThresholds(
        success_rate=success_rate,
        tool_accuracy=tool_accuracy,
        max_policy_violations=max_policy_violations,
    )


def _optional_dict(value: object, path: Path, label: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise Namel3ssError(_suite_error(path, f"{label} must be an object."))
    return dict(value)


def _optional_dict_or_none(value: object, path: Path, label: str) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise Namel3ssError(_suite_error(path, f"{label} must be an object."))
    return dict(value)


def _optional_str_list(value: object, path: Path, label: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise Namel3ssError(_suite_error(path, f"{label} must be a list of strings."))
    items: list[str] = []
    for entry in value:
        if not isinstance(entry, str):
            raise Namel3ssError(_suite_error(path, f"{label} entries must be strings."))
        items.append(entry)
    return items


def _require_optional_str(value: object, path: Path, case_id: str, label: str) -> None:
    if value is None:
        return
    if not isinstance(value, str):
        raise Namel3ssError(_suite_error(path, f"case '{case_id}' tool_bindings.{label} must be a string."))


def _require_optional_bool(value: object, path: Path, case_id: str, label: str) -> None:
    if value is None:
        return
    if not isinstance(value, bool):
        raise Namel3ssError(_suite_error(path, f"case '{case_id}' tool_bindings.{label} must be true/false."))


def _require_optional_int(value: object, path: Path, case_id: str, label: str) -> None:
    if value is None:
        return
    if not isinstance(value, int):
        raise Namel3ssError(_suite_error(path, f"case '{case_id}' tool_bindings.{label} must be an integer."))


def _require_optional_str_list(value: object, path: Path, case_id: str, label: str) -> None:
    if value is None:
        return
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise Namel3ssError(
            _suite_error(path, f"case '{case_id}' tool_bindings.{label} must be a list of strings.")
        )


def _require_optional_str_map(value: object, path: Path, case_id: str, label: str) -> None:
    if value is None:
        return
    if not isinstance(value, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in value.items()):
        raise Namel3ssError(
            _suite_error(path, f"case '{case_id}' tool_bindings.{label} must be an object of strings.")
        )


def _optional_float(value: object, path: Path, label: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    raise Namel3ssError(_suite_error(path, f"{label} must be a number."))


def _optional_int(value: object, path: Path, label: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    raise Namel3ssError(_suite_error(path, f"{label} must be an integer."))


def _require_str(value: object, path: Path, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise Namel3ssError(_suite_error(path, f"{label} must be a non-empty string."))
    return value


def _suite_error(path: Path, message: str) -> str:
    return build_guidance_message(
        what=message,
        why=f"Eval suite path: {path.as_posix()}",
        fix="Update the eval suite JSON and try again.",
        example="n3 eval --json eval_report.json",
    )


__all__ = ["load_eval_suite"]
