from __future__ import annotations

import json
import math
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.tools.python_subprocess import PROTOCOL_VERSION
from namel3ss.runtime.tools.runners.base import ToolRunnerRequest, ToolRunnerResult


class ServiceRunner:
    name = "service"

    def execute(self, request: ToolRunnerRequest) -> ToolRunnerResult:
        url = _resolve_service_url(request)
        timeout_seconds = max(1, math.ceil(request.timeout_ms / 1000))
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
            return ToolRunnerResult(
                ok=False,
                output=None,
                error_type=str(error.get("type") or "ToolError"),
                error_message=str(error.get("message") or "Tool error"),
                metadata={"runner": self.name, "service_url": url, "protocol_version": PROTOCOL_VERSION},
            )
        return ToolRunnerResult(
            ok=True,
            output=response.get("result"),
            error_type=None,
            error_message=None,
            metadata={"runner": self.name, "service_url": url, "protocol_version": PROTOCOL_VERSION},
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
