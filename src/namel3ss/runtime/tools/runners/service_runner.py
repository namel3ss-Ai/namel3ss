from __future__ import annotations

import hashlib
import json
import math
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.capabilities.coverage import required_capabilities
from namel3ss.runtime.capabilities.gates.base import REASON_COVERAGE_MISSING
from namel3ss.runtime.capabilities.model import CapabilityCheck, CapabilityContext
from namel3ss.runtime.tools.python_subprocess import PROTOCOL_VERSION
from namel3ss.runtime.tools.runners.base import ToolRunnerRequest, ToolRunnerResult


class ServiceRunner:
    name = "service"

    def execute(self, request: ToolRunnerRequest) -> ToolRunnerResult:
        url = _resolve_service_url(request)
        timeout_seconds = max(1, math.ceil(request.timeout_ms / 1000))
        handshake_required = request.config.python_tools.service_handshake_required is True
        handshake_result = None
        enforcement_level = None
        unsafe_override_used = False
        if handshake_required:
            handshake_result = _perform_handshake(url, request, timeout_seconds)
            enforcement_level = handshake_result.get("enforcement")
            failure = _enforcement_failure(request, handshake_result, allow_unsafe=request.allow_unsafe)
            if failure is not None:
                metadata = dict(failure.metadata or {})
                metadata.setdefault("runner", self.name)
                metadata.setdefault("service_url", url)
                metadata.setdefault("protocol_version", PROTOCOL_VERSION)
                metadata.setdefault("service_handshake", True)
                if enforcement_level is not None:
                    metadata.setdefault("enforcement_level", enforcement_level)
                return ToolRunnerResult(
                    ok=failure.ok,
                    output=failure.output,
                    error_type=failure.error_type,
                    error_message=failure.error_message,
                    metadata=metadata,
                    capability_checks=failure.capability_checks,
                )
            missing = _missing_guarantees(request, handshake_result.get("supported_guarantees"), str(enforcement_level))
            if request.allow_unsafe and enforcement_level != "enforced" and missing:
                unsafe_override_used = True
        payload = {
            "protocol_version": PROTOCOL_VERSION,
            "tool_name": request.tool_name,
            "kind": request.kind,
            "entry": request.entry,
            "payload": request.payload,
            "timeout_ms": request.timeout_ms,
            "trace_id": request.trace_id,
            "project": {
                "app_root": str(request.app_root),
                "flow": request.flow_name,
            },
        }
        response = _post_json(url, payload, timeout_seconds)
        if not isinstance(response, dict) or "ok" not in response:
            raise Namel3ssError(
                build_guidance_message(
                    what="Tool service returned an invalid response.",
                    why="Expected a JSON object with ok/result or ok/error.",
                    fix="Update the service to follow the tool runner contract.",
                    example='{"ok": true, "result": {"value": 1}}',
                )
            )
        if not response.get("ok"):
            error = response.get("error") or {}
            metadata = {
                "runner": self.name,
                "service_url": url,
                "protocol_version": PROTOCOL_VERSION,
                "service_handshake": bool(handshake_required),
            }
            if handshake_required:
                metadata["enforcement_level"] = enforcement_level
            if unsafe_override_used:
                metadata["unsafe_override"] = True
            return ToolRunnerResult(
                ok=False,
                output=None,
                error_type=str(error.get("type") or "ToolError"),
                error_message=str(error.get("message") or "Tool error"),
                metadata=metadata,
            )
        return ToolRunnerResult(
            ok=True,
            output=response.get("result"),
            error_type=None,
            error_message=None,
            metadata={
                "runner": self.name,
                "service_url": url,
                "protocol_version": PROTOCOL_VERSION,
                "service_handshake": bool(handshake_required),
                **({"enforcement_level": enforcement_level} if handshake_required else {}),
                **({"unsafe_override": True} if unsafe_override_used else {}),
            },
        )


def _resolve_service_url(request: ToolRunnerRequest) -> str:
    url = request.binding.url or request.config.python_tools.service_url
    if url:
        return url
    raise Namel3ssError(
        build_guidance_message(
            what=f'Tool "{request.tool_name}" requires a service URL.',
            why="The binding runner is set to service, but no URL is configured.",
            fix="Add url to the tool binding or set N3_TOOL_SERVICE_URL.",
            example=(
                'tools:\n'
                f'  "{request.tool_name}":\n'
                '    kind: "python"\n'
                '    entry: "tools.my_tool:run"\n'
                '    runner: "service"\n'
                '    url: "http://127.0.0.1:8787/tools"'
            ),
        )
    )


_HANDSHAKE_CACHE: dict[str, dict[str, object]] = {}


def _perform_handshake(url: str, request: ToolRunnerRequest, timeout_seconds: int) -> dict[str, object]:
    key = _handshake_cache_key(url, request)
    cached = _HANDSHAKE_CACHE.get(key)
    if cached is not None:
        return cached
    handshake_url = _handshake_url(url)
    payload = {
        "protocol_version": PROTOCOL_VERSION,
        "tool_name": request.tool_name,
        "runner": "service",
        "required_guarantees": _required_guarantees(request),
    }
    response = _post_json(handshake_url, payload, timeout_seconds)
    if not isinstance(response, dict):
        raise Namel3ssError(
            build_guidance_message(
                what="Tool service handshake returned invalid JSON.",
                why="Expected a JSON object.",
                fix="Update the service to follow the handshake contract.",
                example='{"ok": true, "enforcement": "enforced", "supported_guarantees": {}}',
            )
        )
    _HANDSHAKE_CACHE[key] = response
    return response


def _handshake_cache_key(url: str, request: ToolRunnerRequest) -> str:
    digest = _guarantee_digest(_required_guarantees(request))
    return f"{url}|{request.tool_name}|{digest}"


def _guarantee_digest(guarantees: dict[str, object]) -> str:
    text = json.dumps(guarantees, sort_keys=True, default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _handshake_url(url: str) -> str:
    try:
        from urllib.parse import urlparse

        parsed = urlparse(url)
        return parsed._replace(path="/capabilities/handshake", query="", fragment="").geturl()
    except Exception:
        return url.rstrip("/") + "/capabilities/handshake"


def _required_guarantees(request: ToolRunnerRequest) -> dict[str, object]:
    context = request.capability_context if isinstance(request.capability_context, dict) else {}
    guarantees = context.get("guarantees") if isinstance(context, dict) else {}
    return guarantees if isinstance(guarantees, dict) else {}


def _enforcement_failure(
    request: ToolRunnerRequest,
    handshake: dict[str, object],
    *,
    allow_unsafe: bool,
) -> ToolRunnerResult | None:
    ok = handshake.get("ok")
    if ok is False:
        error = handshake.get("error") or {}
        message = str(error.get("message") or "Service handshake rejected.")
        if allow_unsafe:
            return None
        return ToolRunnerResult(
            ok=False,
            output=None,
            error_type="CapabilityViolation",
            error_message=message,
            metadata={
                "runner": "service",
                "service_handshake": True,
                "enforcement_level": str(handshake.get("enforcement") or "none"),
            },
        )
    enforcement = str(handshake.get("enforcement") or "none")
    supported = handshake.get("supported_guarantees")
    missing = _missing_guarantees(request, supported, enforcement)
    if not missing:
        return None
    if allow_unsafe:
        return None
    message = build_guidance_message(
        what=f'Tool "{request.tool_name}" cannot run on the service runner.',
        why=f"Service enforcement is {enforcement}. Missing guarantees: {', '.join(missing)}.",
        fix="Update the service to enforce the guarantees or switch runners.",
        example=f'n3 tools set-runner "{request.tool_name}" --runner local',
    )
    checks = _build_checks(request, missing)
    return ToolRunnerResult(
        ok=False,
        output=None,
        error_type="CapabilityViolation",
        error_message=message,
        metadata={
            "runner": "service",
            "service_handshake": True,
            "enforcement_level": enforcement,
        },
        capability_checks=checks,
    )


def _missing_guarantees(
    request: ToolRunnerRequest,
    supported: object,
    enforcement: str,
) -> list[str]:
    context = CapabilityContext.from_dict(request.capability_context or {})
    required = required_capabilities(context.guarantees)
    if enforcement != "enforced":
        return required
    if not isinstance(supported, dict):
        return required
    missing: list[str] = []
    if context.guarantees.no_filesystem_read and not supported.get("no_filesystem_read"):
        missing.append("filesystem_read")
    if context.guarantees.no_filesystem_write and not supported.get("no_filesystem_write"):
        missing.append("filesystem_write")
    if context.guarantees.no_network and not supported.get("no_network"):
        missing.append("network")
    if context.guarantees.no_subprocess and not supported.get("no_subprocess"):
        missing.append("subprocess")
    if context.guarantees.no_env_read and not supported.get("no_env_read"):
        missing.append("env_read")
    if context.guarantees.no_env_write and not supported.get("no_env_write"):
        missing.append("env_write")
    if context.guarantees.secrets_allowed is not None:
        supported_secrets = supported.get("secrets_allowed")
        if not isinstance(supported_secrets, list):
            missing.append("secrets")
        else:
            required_secrets = set(context.guarantees.secrets_allowed)
            if not required_secrets.issubset(set(str(item) for item in supported_secrets)):
                missing.append("secrets")
    return missing


def _build_checks(request: ToolRunnerRequest, missing: list[str]) -> list[dict[str, object]]:
    context = CapabilityContext.from_dict(request.capability_context or {})
    checks: list[dict[str, object]] = []
    for capability in missing:
        source = context.guarantees.source_for_capability(capability) or "pack"
        check = CapabilityCheck(
            capability=capability,
            allowed=False,
            guarantee_source=source,
            reason=REASON_COVERAGE_MISSING,
        )
        checks.append(check.to_dict())
    return checks


def _post_json(url: str, payload: dict, timeout_seconds: int) -> dict:
    data = json.dumps(payload).encode("utf-8")
    request = Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            body = response.read()
    except (HTTPError, URLError, TimeoutError) as err:
        raise Namel3ssError(
            build_guidance_message(
                what="Tool service request failed.",
                why=str(err),
                fix="Check the service URL, availability, and timeout.",
                example="N3_TOOL_SERVICE_URL=http://127.0.0.1:8787/tools",
            )
        ) from err
    try:
        return json.loads(body.decode("utf-8"))
    except Exception as err:
        raise Namel3ssError(
            build_guidance_message(
                what="Tool service returned invalid JSON.",
                why=str(err),
                fix="Ensure the service returns JSON responses.",
                example='{"ok": true, "result": {"value": 1}}',
            )
        ) from err


__all__ = ["ServiceRunner"]
