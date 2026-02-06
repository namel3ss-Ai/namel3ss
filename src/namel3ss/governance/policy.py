from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.governance.paths import existing_config_path
from namel3ss.module_loader import load_project
from namel3ss.utils.simple_yaml import parse_yaml


POLICIES_FILENAME = "policies.yaml"
_SNAKE_CASE = re.compile(r"^[a-z][a-z0-9_]*$")
_DECL_RE = re.compile(r'^\s*(flow|route|ai|prompt|record)\s+"([^"]+)"', re.MULTILINE)
_PROVIDER_RE = re.compile(r'^\s*provider\s+is\s+"([^"]+)"', re.MULTILINE)


@dataclass(frozen=True)
class PolicyConfig:
    naming_convention: str | None
    disallowed_model_providers: tuple[str, ...]
    max_token_count_per_request: int | None
    data_residency: str | None


def check_policies_for_app(
    *,
    project_root: str | Path | None,
    app_path: str | Path | None,
) -> dict[str, object]:
    config, config_path = load_policy_config(project_root, app_path)
    if config_path is None or config is None:
        return {
            "ok": True,
            "count": 0,
            "violations": [],
            "policy_path": None,
        }
    project = load_project(app_path)
    violations = check_program_policies(config, project.program)
    return {
        "ok": not violations,
        "count": len(violations),
        "violations": violations,
        "policy_path": config_path.as_posix(),
    }



def enforce_policies_for_app(
    *,
    project_root: str | Path | None,
    app_path: str | Path | None,
) -> None:
    result = check_policies_for_app(project_root=project_root, app_path=app_path)
    if bool(result.get("ok")):
        return
    violations = result.get("violations")
    first = violations[0] if isinstance(violations, list) and violations else {}
    reason = str(first.get("description") or "Policy violation")
    rule_id = str(first.get("rule_id") or "policy")
    raise Namel3ssError(
        _policy_violation_message(rule_id, reason),
        details={
            "category": "policy",
            "reason_code": rule_id,
            "http_status": 403,
        },
    )



def check_policies_for_source(
    *,
    project_root: str | Path | None,
    app_path: str | Path | None,
    source: str,
    source_name: str,
) -> list[dict[str, object]]:
    config, config_path = load_policy_config(project_root, app_path)
    if config is None or config_path is None:
        return []
    violations: list[dict[str, object]] = []
    if config.naming_convention == "snake_case":
        for match in _DECL_RE.finditer(source):
            kind = match.group(1)
            name = match.group(2)
            if not _is_snake_case(name):
                violations.append(
                    _violation(
                        rule_id="naming_convention",
                        description=f"{kind} '{name}' is not snake_case",
                        resource=f"{source_name}:{kind}:{name}",
                    )
                )
    if config.disallowed_model_providers:
        for match in _PROVIDER_RE.finditer(source):
            provider = match.group(1).strip().lower()
            if provider in config.disallowed_model_providers:
                violations.append(
                    _violation(
                        rule_id="disallowed_model_provider",
                        description=f"Provider '{provider}' is disallowed by policy",
                        resource=f"{source_name}:provider:{provider}",
                    )
                )
    violations.sort(key=lambda item: (str(item.get("rule_id")), str(item.get("resource"))))
    return violations



def check_program_policies(config: PolicyConfig, program) -> list[dict[str, object]]:
    violations: list[dict[str, object]] = []
    if config.naming_convention == "snake_case":
        for flow in sorted(getattr(program, "flows", []), key=lambda item: str(getattr(item, "name", ""))):
            name = str(getattr(flow, "name", ""))
            if name and not _is_snake_case(name):
                violations.append(
                    _violation(
                        rule_id="naming_convention",
                        description=f"flow '{name}' is not snake_case",
                        resource=f"flow:{name}",
                    )
                )
        for route in sorted(getattr(program, "routes", []), key=lambda item: str(getattr(item, "name", ""))):
            name = str(getattr(route, "name", ""))
            if name and not _is_snake_case(name):
                violations.append(
                    _violation(
                        rule_id="naming_convention",
                        description=f"route '{name}' is not snake_case",
                        resource=f"route:{name}",
                    )
                )
    if config.disallowed_model_providers:
        ais = getattr(program, "ais", {}) or {}
        for name in sorted(ais.keys()):
            decl = ais[name]
            provider = str(getattr(decl, "provider", "")).strip().lower()
            if provider and provider in config.disallowed_model_providers:
                violations.append(
                    _violation(
                        rule_id="disallowed_model_provider",
                        description=f"AI '{name}' uses disallowed provider '{provider}'",
                        resource=f"ai:{name}",
                    )
                )
    violations.sort(key=lambda item: (str(item.get("rule_id")), str(item.get("resource"))))
    return violations



def check_runtime_request_policies(
    *,
    project_root: str | Path | None,
    app_path: str | Path | None,
    route_name: str,
    flow_name: str,
    payload: dict[str, object] | None,
) -> list[dict[str, object]]:
    config, config_path = load_policy_config(project_root, app_path)
    if config is None or config_path is None:
        return []
    violations: list[dict[str, object]] = []
    if config.max_token_count_per_request is not None:
        tokens = _count_tokens(payload)
        limit = config.max_token_count_per_request
        if tokens > limit:
            violations.append(
                _violation(
                    rule_id="max_token_count_per_request",
                    description=(
                        f"Request tokens {tokens} exceed policy limit {limit} "
                        f"for route '{route_name}' and flow '{flow_name}'"
                    ),
                    resource=f"route:{route_name}",
                )
            )
    violations.sort(key=lambda item: (str(item.get("rule_id")), str(item.get("resource"))))
    return violations



def enforce_runtime_request_policies(
    *,
    project_root: str | Path | None,
    app_path: str | Path | None,
    route_name: str,
    flow_name: str,
    payload: dict[str, object] | None,
) -> None:
    violations = check_runtime_request_policies(
        project_root=project_root,
        app_path=app_path,
        route_name=route_name,
        flow_name=flow_name,
        payload=payload,
    )
    if not violations:
        return
    first = violations[0]
    rule_id = str(first.get("rule_id") or "policy")
    reason = str(first.get("description") or "Policy violation")
    raise Namel3ssError(
        _policy_violation_message(rule_id, reason),
        details={
            "category": "policy",
            "reason_code": rule_id,
            "http_status": 403,
        },
    )



def load_policy_config(
    project_root: str | Path | None,
    app_path: str | Path | None,
) -> tuple[PolicyConfig | None, Path | None]:
    path = existing_config_path(project_root, app_path, primary_name=POLICIES_FILENAME)
    if path is None or not path.exists():
        return None, None
    try:
        payload = parse_yaml(path.read_text(encoding="utf-8"))
    except Exception as err:
        raise Namel3ssError(_invalid_policy_message(path)) from err
    if not isinstance(payload, dict):
        raise Namel3ssError(_invalid_policy_message(path))

    naming = str(payload.get("naming_convention") or "").strip().lower() or None
    disallowed = tuple(sorted(set(_normalize_text_list(payload.get("disallowed_model_providers")))))

    max_tokens = payload.get("max_token_count_per_request")
    if max_tokens is None:
        max_tokens = payload.get("max_token_count")
    if isinstance(max_tokens, str) and max_tokens.isdigit():
        max_tokens_value = int(max_tokens)
    elif isinstance(max_tokens, int):
        max_tokens_value = max_tokens
    else:
        max_tokens_value = None

    residency = str(payload.get("data_residency") or "").strip() or None

    return (
        PolicyConfig(
            naming_convention=naming,
            disallowed_model_providers=disallowed,
            max_token_count_per_request=max_tokens_value,
            data_residency=residency,
        ),
        path,
    )



def _count_tokens(value: object) -> int:
    if value is None:
        return 0
    if isinstance(value, str):
        return len([part for part in value.split() if part.strip()])
    if isinstance(value, dict):
        return sum(_count_tokens(item) for item in value.values())
    if isinstance(value, list):
        return sum(_count_tokens(item) for item in value)
    if isinstance(value, tuple):
        return sum(_count_tokens(item) for item in value)
    if isinstance(value, set):
        return sum(_count_tokens(item) for item in sorted(value, key=lambda item: str(item)))
    return 0



def _is_snake_case(name: str) -> bool:
    return bool(_SNAKE_CASE.match(name))



def _normalize_text_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip().lower()
        return [text] if text else []
    if isinstance(value, (list, tuple, set)):
        items = sorted(value, key=lambda item: str(item)) if isinstance(value, set) else value
        out: list[str] = []
        for item in items:
            text = str(item).strip().lower()
            if text:
                out.append(text)
        return out
    text = str(value).strip().lower()
    return [text] if text else []



def _violation(*, rule_id: str, description: str, resource: str) -> dict[str, object]:
    return {
        "rule_id": rule_id,
        "description": description,
        "resource": resource,
    }



def _invalid_policy_message(path: Path) -> str:
    return build_guidance_message(
        what="Policy config is invalid.",
        why=f"Could not parse {path.as_posix()}.",
        fix="Use valid YAML keys for policy rules.",
        example=(
            "naming_convention: snake_case\n"
            "disallowed_model_providers:\n"
            "  - openai\n"
            "max_token_count_per_request: 4000"
        ),
    )



def _policy_violation_message(rule_id: str, description: str) -> str:
    return build_guidance_message(
        what=f"Policy '{rule_id}' blocked this action.",
        why=description,
        fix="Update policies.yaml or adjust the app/request to satisfy policy.",
        example="n3 policy check --json",
    )


__all__ = [
    "POLICIES_FILENAME",
    "PolicyConfig",
    "check_policies_for_app",
    "check_policies_for_source",
    "check_program_policies",
    "check_runtime_request_policies",
    "enforce_policies_for_app",
    "enforce_runtime_request_policies",
    "load_policy_config",
]
