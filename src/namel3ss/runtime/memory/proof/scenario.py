from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from namel3ss.errors.base import Namel3ssError


class ScenarioError(Namel3ssError):
    pass


@dataclass(frozen=True)
class MemoryProfileSpec:
    short_term: int
    semantic: bool
    profile: bool


@dataclass(frozen=True)
class AIProfileSpec:
    name: str
    model: str
    provider: str
    system_prompt: str | None
    exposed_tools: list[str]
    memory: MemoryProfileSpec


@dataclass(frozen=True)
class ScenarioStep:
    kind: str
    payload: dict


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    name: str
    ai_profile: AIProfileSpec
    identity: dict
    initial_state: dict
    steps: list[ScenarioStep]
    source_path: Path


def list_scenario_paths(root: Path) -> list[Path]:
    if not root.exists():
        return []
    paths = [path for path in root.iterdir() if path.suffix in {".yaml", ".yml", ".json"}]
    return sorted(paths, key=lambda path: path.name)


def load_scenario(path: Path) -> Scenario:
    if not path.exists():
        raise ScenarioError(f"Scenario file not found: {path}")
    raw = _load_payload(path)
    if not isinstance(raw, dict):
        raise ScenarioError(f"Scenario payload must be a mapping. Got {type(raw).__name__}.")
    scenario_id = path.stem
    name = _require_str(raw.get("name"), "name", path)
    ai_profile = _parse_ai_profile(raw.get("ai_profile"), path)
    identity = _optional_dict(raw.get("identity"), "identity", path)
    initial_state = _optional_dict(raw.get("initial_state"), "initial_state", path)
    steps = _parse_steps(raw.get("steps"), path)
    return Scenario(
        scenario_id=scenario_id,
        name=name,
        ai_profile=ai_profile,
        identity=identity,
        initial_state=initial_state,
        steps=steps,
        source_path=path,
    )


def _load_payload(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        return json.loads(text)
    if path.suffix in {".yaml", ".yml"}:
        try:
            return _parse_yaml(text)
        except _YamlError as exc:
            raise ScenarioError(f"{path.name}: YAML parse failed. {exc}") from exc
    raise ScenarioError(f"Unsupported scenario format: {path.suffix}")


def _parse_ai_profile(value: object, path: Path) -> AIProfileSpec:
    if not isinstance(value, dict):
        raise ScenarioError(_error_prefix(path, "ai_profile") + "must be a mapping.")
    name = _require_str(value.get("name"), "ai_profile.name", path)
    model = _coerce_str(value.get("model"), "mock-model")
    provider = _coerce_str(value.get("provider"), "mock")
    system_prompt = _optional_str(value.get("system_prompt"))
    exposed_tools = _optional_list(value.get("exposed_tools"), "ai_profile.exposed_tools", path)
    memory = _parse_memory_profile(value.get("memory"), path)
    return AIProfileSpec(
        name=name,
        model=model,
        provider=provider,
        system_prompt=system_prompt,
        exposed_tools=exposed_tools,
        memory=memory,
    )


def _parse_memory_profile(value: object, path: Path) -> MemoryProfileSpec:
    if not isinstance(value, dict):
        raise ScenarioError(_error_prefix(path, "ai_profile.memory") + "must be a mapping.")
    short_term = _require_int(value.get("short_term"), "ai_profile.memory.short_term", path)
    semantic = _require_bool(value.get("semantic"), "ai_profile.memory.semantic", path)
    profile = _require_bool(value.get("profile"), "ai_profile.memory.profile", path)
    return MemoryProfileSpec(short_term=short_term, semantic=semantic, profile=profile)


def _parse_steps(value: object, path: Path) -> list[ScenarioStep]:
    if not isinstance(value, list) or not value:
        raise ScenarioError(_error_prefix(path, "steps") + "must be a non-empty list.")
    steps: list[ScenarioStep] = []
    for idx, entry in enumerate(value, start=1):
        if not isinstance(entry, dict) or len(entry) != 1:
            raise ScenarioError(
                _error_prefix(path, f"steps[{idx}]") + "must be a mapping with a single step type."
            )
        kind, payload = next(iter(entry.items()))
        if kind not in {"recall", "record", "admin"}:
            raise ScenarioError(_error_prefix(path, f"steps[{idx}]") + f"unknown step type '{kind}'.")
        payload = payload or {}
        if not isinstance(payload, dict):
            raise ScenarioError(_error_prefix(path, f"steps[{idx}].{kind}") + "must be a mapping.")
        _validate_step_payload(kind, payload, path, idx)
        steps.append(ScenarioStep(kind=kind, payload=payload))
    return steps


def _validate_step_payload(kind: str, payload: dict, path: Path, idx: int) -> None:
    prefix = _error_prefix(path, f"steps[{idx}].{kind}.")
    if kind == "recall":
        _require_str(payload.get("input"), prefix + "input", path)
        if "agent_id" in payload and payload["agent_id"] is not None:
            _require_str(payload.get("agent_id"), prefix + "agent_id", path)
        return
    if kind == "record":
        _require_str(payload.get("input"), prefix + "input", path)
        _require_str(payload.get("output"), prefix + "output", path)
        tool_events = payload.get("tool_events", [])
        if tool_events is None:
            tool_events = []
        if not isinstance(tool_events, list):
            raise ScenarioError(prefix + "tool_events must be a list.")
        if "agent_id" in payload and payload["agent_id"] is not None:
            _require_str(payload.get("agent_id"), prefix + "agent_id", path)
        return
    if kind == "admin":
        action = _require_str(payload.get("action"), prefix + "action", path)
        if action not in {
            "propose_rule",
            "apply_agreement",
            "create_handoff",
            "apply_handoff",
            "compute_impact",
            "advance_phase",
        }:
            raise ScenarioError(prefix + f"action '{action}' is not supported.")
        if "payload" in payload and payload["payload"] is not None and not isinstance(payload["payload"], dict):
            raise ScenarioError(prefix + "payload must be a mapping if provided.")


def _optional_dict(value: object, label: str, path: Path) -> dict:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ScenarioError(_error_prefix(path, label) + "must be a mapping.")
    return value


def _optional_list(value: object, label: str, path: Path) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ScenarioError(_error_prefix(path, label) + "must be a list.")
    for entry in value:
        if not isinstance(entry, str):
            raise ScenarioError(_error_prefix(path, label) + "entries must be strings.")
    return value


def _require_str(value: object, label: str, path: Path) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ScenarioError(_error_prefix(path, label) + "must be a non-empty string.")
    return value


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def _require_int(value: object, label: str, path: Path) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ScenarioError(_error_prefix(path, label) + "must be an integer.")
    return int(value)


def _require_bool(value: object, label: str, path: Path) -> bool:
    if not isinstance(value, bool):
        raise ScenarioError(_error_prefix(path, label) + "must be true or false.")
    return bool(value)


def _coerce_str(value: object, default: str) -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _error_prefix(path: Path, label: str) -> str:
    return f"{path.name}:{label} "


class _YamlError(Exception):
    pass


def _parse_yaml(text: str) -> dict:
    lines = _tokenize_yaml(text)
    payload, next_idx = _parse_block(lines, 0, 0)
    if next_idx < len(lines):
        raise _YamlError("Unexpected trailing content.")
    if not isinstance(payload, dict):
        raise _YamlError("Scenario root must be a mapping.")
    return payload


def _tokenize_yaml(text: str) -> list[tuple[int, str]]:
    lines: list[tuple[int, str]] = []
    for raw in text.splitlines():
        cleaned = _strip_comment(raw.rstrip())
        if not cleaned.strip():
            continue
        if "\t" in cleaned:
            raise _YamlError("Tabs are not allowed in YAML.")
        indent = len(cleaned) - len(cleaned.lstrip(" "))
        if indent % 2 != 0:
            raise _YamlError("Indentation must use 2 spaces.")
        lines.append((indent, cleaned.strip()))
    return lines


def _strip_comment(line: str) -> str:
    in_single = False
    in_double = False
    for idx, ch in enumerate(line):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            return line[:idx]
    return line


def _parse_block(lines: list[tuple[int, str]], start: int, indent: int) -> tuple[Any, int]:
    idx = _skip_empty(lines, start)
    if idx >= len(lines):
        return {}, idx
    line_indent, content = lines[idx]
    if line_indent < indent:
        return {}, idx
    if content.startswith("- "):
        return _parse_list(lines, idx, indent)
    return _parse_dict(lines, idx, indent)


def _parse_list(lines: list[tuple[int, str]], start: int, indent: int) -> tuple[list, int]:
    items: list = []
    idx = start
    while idx < len(lines):
        line_indent, content = lines[idx]
        if line_indent < indent:
            break
        if line_indent > indent:
            raise _YamlError("List item indentation is invalid.")
        if not content.startswith("- "):
            break
        item_text = content[2:].strip()
        if not item_text:
            value, idx = _parse_block(lines, idx + 1, indent + 2)
            items.append(value)
            continue
        if ":" in item_text and not item_text.startswith(("'", '"')):
            key, rest = item_text.split(":", 1)
            key = key.strip()
            rest = rest.strip()
            if not key:
                raise _YamlError("List mapping key is empty.")
            if rest:
                items.append({key: _parse_scalar(rest)})
                idx += 1
            else:
                value, idx = _parse_block(lines, idx + 1, indent + 2)
                items.append({key: value})
            continue
        items.append(_parse_scalar(item_text))
        idx += 1
    return items, idx


def _parse_dict(lines: list[tuple[int, str]], start: int, indent: int) -> tuple[dict, int]:
    data: dict = {}
    idx = start
    while idx < len(lines):
        line_indent, content = lines[idx]
        if line_indent < indent:
            break
        if line_indent > indent:
            raise _YamlError("Mapping indentation is invalid.")
        if content.startswith("- "):
            break
        if ":" not in content:
            raise _YamlError("Mapping entry must contain a colon.")
        key, rest = content.split(":", 1)
        key = key.strip()
        rest = rest.strip()
        if not key:
            raise _YamlError("Mapping key is empty.")
        if rest:
            data[key] = _parse_scalar(rest)
            idx += 1
        else:
            value, idx = _parse_block(lines, idx + 1, indent + 2)
            data[key] = value
    return data, idx


def _skip_empty(lines: list[tuple[int, str]], start: int) -> int:
    idx = start
    while idx < len(lines):
        if lines[idx][1]:
            return idx
        idx += 1
    return idx


def _parse_scalar(value: str) -> object:
    if value in {"null", "Null", "NULL", "~"}:
        return None
    if value in {"true", "True", "TRUE"}:
        return True
    if value in {"false", "False", "FALSE"}:
        return False
    if value.startswith("[") or value.startswith("{"):
        try:
            return json.loads(value)
        except json.JSONDecodeError as exc:
            raise _YamlError(f"Inline JSON parse failed: {exc}") from exc
    if (value.startswith("\"") and value.endswith("\"")) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    if value.isdigit() or (value.startswith("-") and value[1:].isdigit()):
        return int(value)
    return value


__all__ = [
    "AIProfileSpec",
    "MemoryProfileSpec",
    "Scenario",
    "ScenarioError",
    "ScenarioStep",
    "list_scenario_paths",
    "load_scenario",
]
