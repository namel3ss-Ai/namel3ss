from __future__ import annotations

from namel3ss.docs.sdk_shared import _collect_operations, _resolve_base_url, _snake_case


def generate_python_client(spec: dict) -> str:
    operations = _collect_operations(spec)
    base_url = _resolve_base_url(spec)
    lines: list[str] = []
    lines.append("from __future__ import annotations")
    lines.append("")
    lines.append("from typing import Any, Dict, Optional")
    lines.append("import base64")
    lines.append("import json")
    lines.append("import requests")
    lines.append("")
    lines.append("")
    lines.append("class ApiError(Exception):")
    lines.append("    def __init__(self, code: str, message: str, remediation: str, status: int) -> None:")
    lines.append("        super().__init__(f\"{code}: {message}\")")
    lines.append("        self.code = code")
    lines.append("        self.message = message")
    lines.append("        self.remediation = remediation")
    lines.append("        self.status = status")
    lines.append("")
    lines.append("")
    lines.append("def _decode_toon(token: str) -> Dict[str, Any]:")
    lines.append("    padded = token + \"=\" * ((4 - len(token) % 4) % 4)")
    lines.append("    raw = base64.urlsafe_b64decode(padded.encode(\"ascii\"))")
    lines.append("    return json.loads(raw.decode(\"utf-8\")) if raw else {}")
    lines.append("")
    lines.append("")
    lines.append("def _raise_api_error(response: requests.Response) -> None:")
    lines.append("    try:")
    lines.append("        payload = response.json()")
    lines.append("    except Exception:")
    lines.append("        raise ApiError(\"http_error\", f\"Request failed with {response.status_code}\", \"Check the request and try again.\", response.status_code)")
    lines.append("    code = str(payload.get(\"code\") or \"http_error\")")
    lines.append("    message = str(payload.get(\"message\") or \"Request failed\")")
    lines.append("    remediation = str(payload.get(\"remediation\") or \"Check the request and try again.\")")
    lines.append("    raise ApiError(code, message, remediation, response.status_code)")
    lines.append("")
    lines.append("")
    lines.append("class Client:")
    lines.append(f'    def __init__(self, base_url: str = \"{base_url}\") -> None:')
    lines.append("        self.base_url = base_url.rstrip('/')")
    lines.append("")
    if not operations:
        lines.append("    pass")
        return "\n".join(lines) + "\n"
    for op in operations:
        method_name = _snake_case(op.name)
        lines.append(f"    def {method_name}(")
        lines.append("        self,")
        lines.append("        *,")
        lines.append("        path: Optional[Dict[str, Any]] = None,")
        lines.append("        query: Optional[Dict[str, Any]] = None,")
        if op.request_schema:
            lines.append("        body: Optional[Dict[str, Any]] = None,")
        lines.append("        format: Optional[str] = None,")
        lines.append("    ) -> Dict[str, Any]:")
        lines.append("        path_params = path or {}")
        lines.append(f'        url = self.base_url + \"{op.path}\".format(**path_params)')
        lines.append("        params = query or {}")
        lines.append("        if format:")
        lines.append("            params[\"format\"] = format")
        if op.request_schema and op.method.upper() not in {"GET", "HEAD"}:
            lines.append(f'        response = requests.{op.method.lower()}(url, params=params, json=body)')
        else:
            lines.append(f'        response = requests.{op.method.lower()}(url, params=params)')
        lines.append("        if not response.ok:")
        lines.append("            _raise_api_error(response)")
        lines.append("        if format == \"toon\":")
        lines.append("            return _decode_toon(response.text)")
        lines.append("        return response.json()")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


__all__ = ["generate_python_client"]
