from __future__ import annotations

import re

from namel3ss.docs.sdk_shared import (
    _collect_component_schemas,
    _collect_operations,
    _ensure_operation_types,
    _merge_types,
    _pascal_case,
    _schema_is_object,
    _schema_ref_name,
)
from namel3ss.utils.slugify import slugify_text


def generate_rust_client(spec: dict) -> dict[str, str]:
    operations = _collect_operations(spec)
    components = _collect_component_schemas(spec)
    extra_types: dict[str, dict] = {}
    for op in operations:
        _ensure_operation_types(op, extra_types, components)
    type_defs = _merge_types(components, extra_types)
    crate_name = _rust_crate_name(spec)
    lines: list[str] = []
    lines.append("use base64::engine::general_purpose::URL_SAFE;")
    lines.append("use base64::Engine;")
    lines.append("use reqwest::blocking::Client as HttpClient;")
    lines.append("use serde::{Deserialize, Serialize};")
    lines.append("use serde_json::Value;")
    lines.append("")
    lines.append("#[derive(Debug, Clone, Serialize, Deserialize)]")
    lines.append("pub struct ErrorEnvelope {")
    lines.append("    pub code: String,")
    lines.append("    pub message: String,")
    lines.append("    pub remediation: String,")
    lines.append("}")
    lines.append("")
    lines.append("#[derive(Debug, Clone)]")
    lines.append("pub struct ApiError {")
    lines.append("    pub status: u16,")
    lines.append("    pub envelope: ErrorEnvelope,")
    lines.append("}")
    lines.append("")
    lines.append("impl std::fmt::Display for ApiError {")
    lines.append("    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {")
    lines.append("        write!(f, \"{}: {}\", self.envelope.code, self.envelope.message)")
    lines.append("    }")
    lines.append("}")
    lines.append("")
    lines.append("impl std::error::Error for ApiError {}")
    lines.append("")
    lines.extend(_render_rust_types(type_defs, components))
    lines.append("")
    lines.append("#[derive(Debug, Clone)]")
    lines.append("pub struct Client {")
    lines.append("    base_url: String,")
    lines.append("    http: HttpClient,")
    lines.append("}")
    lines.append("")
    lines.append("impl Client {")
    lines.append("    pub fn new(base_url: Option<&str>) -> Self {")
    lines.append("        let base = base_url.unwrap_or(\"http://127.0.0.1:7340\").trim_end_matches('/').to_string();")
    lines.append("        Self { base_url: base, http: HttpClient::new() }")
    lines.append("    }")
    lines.append("")
    lines.append("    fn decode_toon(&self, token: &str) -> Result<Value, ApiError> {")
    lines.append("        let pad = \"=\".repeat((4 - (token.len() % 4)) % 4);")
    lines.append("        let padded = format!(\"{}{}\", token, pad);")
    lines.append("        let raw = URL_SAFE.decode(padded.as_bytes()).unwrap_or_default();")
    lines.append("        let value: Value = serde_json::from_slice(&raw).unwrap_or(Value::Null);")
    lines.append("        Ok(value)")
    lines.append("    }")
    for op in operations:
        lines.append("")
        lines.extend(_render_rust_method(op, components))
    lines.append("}")
    lib_rs = "\n".join(lines).rstrip() + "\n"
    cargo = "\n".join(
        [
            "[package]",
            f"name = \"{crate_name}\"",
            "version = \"0.1.0\"",
            "edition = \"2021\"",
            "",
            "[dependencies]",
            "reqwest = { version = \"0.11\", features = [\"json\", \"blocking\"] }",
            "serde = { version = \"1.0\", features = [\"derive\"] }",
            "serde_json = \"1.0\"",
            "base64 = \"0.21\"",
            "urlencoding = \"2.1\"",
            "",
        ]
    )
    return {"Cargo.toml": cargo, "src/lib.rs": lib_rs}


def _rust_type_from_schema(schema: dict | None, components: dict[str, dict]) -> str:
    if not isinstance(schema, dict):
        return "Value"
    ref = _schema_ref_name(schema)
    if ref:
        return ref
    schema_type = schema.get("type")
    if schema_type == "string":
        return "String"
    if schema_type == "number":
        return "f64"
    if schema_type == "integer":
        return "i64"
    if schema_type == "boolean":
        return "bool"
    if schema_type == "array":
        items = schema.get("items") if isinstance(schema.get("items"), dict) else None
        return f"Vec<{_rust_type_from_schema(items, components)}>"
    if schema_type == "object":
        if _schema_is_object(schema):
            return "Value"
        return "Value"
    return "Value"


def _render_rust_types(type_defs: dict[str, dict], components: dict[str, dict]) -> list[str]:
    lines: list[str] = []
    for name in sorted(type_defs.keys()):
        schema = type_defs[name]
        if not _schema_is_object(schema):
            continue
        properties = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
        required = set(schema.get("required") or [])
        lines.append("#[derive(Debug, Clone, Serialize, Deserialize)]")
        lines.append(f"pub struct {name} {{")
        for field_name in sorted(properties.keys()):
            field_schema = properties[field_name]
            field_type = _rust_type_from_schema(field_schema, components)
            if field_name not in required:
                field_type = f"Option<{field_type}>"
            lines.append(f"    #[serde(rename = \"{field_name}\")]")
            lines.append(f"    pub {_rust_field_name(field_name)}: {field_type},")
        lines.append("}")
        lines.append("")
    return lines


def _render_rust_method(op, components: dict[str, dict]) -> list[str]:
    lines: list[str] = []
    name = _pascal_case(op.name)
    params_name = f"{name}Params" if (op.path_params or op.query_params) else ""
    request_type = _rust_operation_type(op.request_schema, components, f"{name}Request")
    response_type = _rust_operation_type(op.response_schema, components, f"{name}Response")
    signature_parts: list[str] = ["&self"]
    if params_name:
        signature_parts.append(f"params: {params_name}")
    if op.request_schema:
        signature_parts.append(f"body: {request_type}")
    signature_parts.append("format: Option<&str>")
    signature = ", ".join(signature_parts)
    lines.append(f"    pub fn {_rust_method_name(op.name)}({signature}) -> Result<{response_type}, ApiError> {{")
    lines.append(f"        let mut path = \"{op.path}\".to_string();")
    for param in op.path_params:
        lines.append(
            f"        path = path.replace(\"{{{param.name}}}\", &urlencoding::encode(&params.{_rust_field_name(param.name)}.to_string()));"
        )
    lines.append("        let mut query: Vec<(String, String)> = Vec::new();")
    for param in op.query_params:
        field = _rust_field_name(param.name)
        if param.required:
            lines.append(f"        query.push((\"{param.name}\".to_string(), params.{field}.to_string()));")
        else:
            lines.append(f"        if let Some(value) = &params.{field} {{")
            lines.append(f"            query.push((\"{param.name}\".to_string(), value.to_string()));")
            lines.append("        }")
    lines.append("        if let Some(fmt_value) = format {")
    lines.append("            query.push((\"format\".to_string(), fmt_value.to_string()));")
    lines.append("        }")
    lines.append("        let url = format!(\"{}{}\", self.base_url, path);")
    lines.append("        let mut request = self.http.request(reqwest::Method::from_bytes(b\"" + op.method.upper() + "\").unwrap(), &url);")
    lines.append("        if !query.is_empty() {")
    lines.append("            request = request.query(&query);")
    lines.append("        }")
    if op.request_schema:
        lines.append("        request = request.json(&body);")
    lines.append("        let response = request.send();")
    lines.append("        if response.is_err() {")
    lines.append("            return Err(ApiError { status: 0, envelope: ErrorEnvelope { code: \"http_error\".to_string(), message: \"Request failed\".to_string(), remediation: \"Check the request and try again.\".to_string() } });")
    lines.append("        }")
    lines.append("        let response = response.unwrap();")
    lines.append("        let status = response.status().as_u16();")
    lines.append("        let text = response.text().unwrap_or_default();")
    lines.append("        if status >= 400 {")
    lines.append("            let envelope: ErrorEnvelope = serde_json::from_str(&text).unwrap_or(ErrorEnvelope { code: \"http_error\".to_string(), message: \"Request failed\".to_string(), remediation: \"Check the request and try again.\".to_string() });")
    lines.append("            return Err(ApiError { status, envelope });")
    lines.append("        }")
    lines.append("        if let Some(fmt_value) = format {")
    lines.append("            if fmt_value == \"toon\" {")
    lines.append("                let decoded = self.decode_toon(&text)?;")
    lines.append("                let parsed: Result<" + response_type + ", _> = serde_json::from_value(decoded);")
    lines.append("                if let Ok(out) = parsed {")
    lines.append("                    return Ok(out);")
    lines.append("                }")
    lines.append("                let envelope = ErrorEnvelope { code: \"decode_error\".to_string(), message: \"Response decode failed\".to_string(), remediation: \"Check the response format.\".to_string() };")
    lines.append("                return Err(ApiError { status: 200, envelope });")
    lines.append("            }")
    lines.append("        }")
    lines.append("        let parsed: Result<" + response_type + ", _> = serde_json::from_str(&text);")
    lines.append("        if let Ok(out) = parsed {")
    lines.append("            return Ok(out);")
    lines.append("        }")
    lines.append("        let envelope = ErrorEnvelope { code: \"decode_error\".to_string(), message: \"Response decode failed\".to_string(), remediation: \"Check the response format.\".to_string() };")
    lines.append("        Err(ApiError { status: 200, envelope })")
    lines.append("    }")
    return lines


def _rust_operation_type(schema: dict | None, components: dict[str, dict], default_name: str) -> str:
    if schema is None:
        return "Value"
    ref = _schema_ref_name(schema)
    if ref:
        return ref
    if _schema_is_object(schema):
        return default_name
    return _rust_type_from_schema(schema, components)


def _rust_crate_name(spec: dict) -> str:
    title = (spec.get("info") or {}).get("title") or "namel3ss_sdk"
    slug = slugify_text(str(title)) or "namel3ss_sdk"
    return slug.replace("-", "_")


def _rust_field_name(name: str) -> str:
    cleaned = re.sub(r"[^0-9A-Za-z_]+", "_", name).strip("_").lower()
    return cleaned or "value"


def _rust_method_name(name: str) -> str:
    cleaned = re.sub(r"[^0-9A-Za-z_]+", "_", name).strip("_")
    if not cleaned:
        return "call"
    return cleaned.lower()


__all__ = ["generate_rust_client"]
