from __future__ import annotations

from namel3ss.runtime.packs.broker import http_get_json


def run(payload):
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")
    url = payload.get("url")
    if not isinstance(url, str) or not url.strip():
        raise ValueError("payload.url must be a non-empty string")
    stub = payload.get("stub_response")
    if stub is not None:
        if not isinstance(stub, dict):
            raise ValueError("payload.stub_response must be an object")
        return stub
    headers = payload.get("headers")
    if headers is not None and not isinstance(headers, dict):
        raise ValueError("payload.headers must be an object")
    timeout = payload.get("timeout_seconds", 10)
    if not isinstance(timeout, int) or timeout <= 0:
        raise ValueError("payload.timeout_seconds must be a positive integer")
    return http_get_json(url.strip(), headers=headers, timeout_seconds=timeout)
