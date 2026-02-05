from __future__ import annotations

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


def generate_go_client(spec: dict) -> dict[str, str]:
    operations = _collect_operations(spec)
    components = _collect_component_schemas(spec)
    extra_types: dict[str, dict] = {}
    for op in operations:
        _ensure_operation_types(op, extra_types, components)
    type_defs = _merge_types(components, extra_types)
    module_name = _go_module_name(spec)
    lines: list[str] = []
    lines.append("package namel3ss")
    lines.append("")
    lines.append("import (")
    lines.append("  \"bytes\"")
    lines.append("  \"encoding/base64\"")
    lines.append("  \"encoding/json\"")
    lines.append("  \"fmt\"")
    lines.append("  \"io\"")
    lines.append("  \"net/http\"")
    lines.append("  \"net/url\"")
    lines.append("  \"strings\"")
    lines.append(")")
    lines.append("")
    lines.append("type Json map[string]any")
    lines.append("")
    lines.append("type ErrorEnvelope struct {")
    lines.append("  Code string `json:\"code\"`")
    lines.append("  Message string `json:\"message\"`")
    lines.append("  Remediation string `json:\"remediation\"`")
    lines.append("}")
    lines.append("")
    lines.append("type ApiError struct {")
    lines.append("  Status int")
    lines.append("  Envelope ErrorEnvelope")
    lines.append("}")
    lines.append("")
    lines.append("func (e ApiError) Error() string {")
    lines.append("  return fmt.Sprintf(\"%s: %s\", e.Envelope.Code, e.Envelope.Message)")
    lines.append("}")
    lines.append("")
    lines.extend(_render_go_types(type_defs, components))
    lines.append("")
    lines.append("type Client struct {")
    lines.append("  BaseURL string")
    lines.append("  HTTPClient *http.Client")
    lines.append("}")
    lines.append("")
    lines.append("func NewClient(baseURL string) *Client {")
    lines.append("  if strings.TrimSpace(baseURL) == \"\" {")
    lines.append("    baseURL = \"http://127.0.0.1:7340\"")
    lines.append("  }")
    lines.append("  return &Client{BaseURL: strings.TrimRight(baseURL, \"/\"), HTTPClient: &http.Client{}}")
    lines.append("}")
    lines.append("")
    lines.append("func decodeToon(token string) ([]byte, error) {")
    lines.append("  padded := token + strings.Repeat(\"=\", (4 - (len(token) % 4)) % 4)")
    lines.append("  raw, err := base64.URLEncoding.DecodeString(padded)")
    lines.append("  if err != nil {")
    lines.append("    return nil, err")
    lines.append("  }")
    lines.append("  return raw, nil")
    lines.append("}")
    lines.append("")
    lines.append("func (c *Client) doRequest(method string, path string, query url.Values, body any) ([]byte, error) {")
    lines.append("  urlStr := c.BaseURL + path")
    lines.append("  if len(query) > 0 {")
    lines.append("    urlStr = urlStr + \"?\" + query.Encode()")
    lines.append("  }")
    lines.append("  var reader io.Reader")
    lines.append("  if body != nil {")
    lines.append("    raw, err := json.Marshal(body)")
    lines.append("    if err != nil {")
    lines.append("      return nil, err")
    lines.append("    }")
    lines.append("    reader = bytes.NewReader(raw)")
    lines.append("  }")
    lines.append("  req, err := http.NewRequest(method, urlStr, reader)")
    lines.append("  if err != nil {")
    lines.append("    return nil, err")
    lines.append("  }")
    lines.append("  if body != nil {")
    lines.append("    req.Header.Set(\"Content-Type\", \"application/json\")")
    lines.append("  }")
    lines.append("  client := c.HTTPClient")
    lines.append("  if client == nil {")
    lines.append("    client = &http.Client{}")
    lines.append("  }")
    lines.append("  resp, err := client.Do(req)")
    lines.append("  if err != nil {")
    lines.append("    return nil, err")
    lines.append("  }")
    lines.append("  defer resp.Body.Close()")
    lines.append("  data, err := io.ReadAll(resp.Body)")
    lines.append("  if err != nil {")
    lines.append("    return nil, err")
    lines.append("  }")
    lines.append("  if resp.StatusCode >= 400 {")
    lines.append("    env := ErrorEnvelope{Code: \"http_error\", Message: \"Request failed\", Remediation: \"Check the request and try again.\"}")
    lines.append("    _ = json.Unmarshal(data, &env)")
    lines.append("    return nil, ApiError{Status: resp.StatusCode, Envelope: env}")
    lines.append("  }")
    lines.append("  return data, nil")
    lines.append("}")
    for op in operations:
        lines.append("")
        lines.extend(_render_go_method(op, components))
    code = "\n".join(lines).rstrip() + "\n"
    go_mod = f"module {module_name}\n\ngo 1.20\n"
    return {"client.go": code, "go.mod": go_mod}


def _go_type_from_schema(schema: dict | None, components: dict[str, dict]) -> str:
    if not isinstance(schema, dict):
        return "Json"
    ref = _schema_ref_name(schema)
    if ref:
        return ref
    schema_type = schema.get("type")
    if schema_type == "string":
        return "string"
    if schema_type == "number":
        return "float64"
    if schema_type == "integer":
        return "int64"
    if schema_type == "boolean":
        return "bool"
    if schema_type == "array":
        items = schema.get("items") if isinstance(schema.get("items"), dict) else None
        return f"[]{_go_type_from_schema(items, components)}"
    if schema_type == "object":
        if _schema_is_object(schema):
            return "Json"
        return "map[string]any"
    return "Json"


def _render_go_types(type_defs: dict[str, dict], components: dict[str, dict]) -> list[str]:
    lines: list[str] = []
    for name in sorted(type_defs.keys()):
        schema = type_defs[name]
        if not _schema_is_object(schema):
            continue
        properties = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
        required = set(schema.get("required") or [])
        lines.append(f"type {name} struct {{")
        for field_name in sorted(properties.keys()):
            field_schema = properties[field_name]
            field_type = _go_type_from_schema(field_schema, components)
            optional = field_name not in required
            if optional and not field_type.startswith("[]") and not field_type.startswith("map"):
                field_type = f"*{field_type}"
            tag = f'`json:\"{field_name}{" ,omitempty" if optional else ""}\"`'
            tag = tag.replace(" ,omitempty", ",omitempty")
            lines.append(f"  {_pascal_case(field_name)} {field_type} {tag}")
        lines.append("}")
        lines.append("")
    return lines


def _render_go_method(op, components: dict[str, dict]) -> list[str]:
    lines: list[str] = []
    name = _pascal_case(op.name)
    params_name = f"{name}Params" if (op.path_params or op.query_params) else ""
    request_type = _go_operation_type(op.request_schema, components, f"{name}Request")
    response_type = _go_operation_type(op.response_schema, components, f"{name}Response")
    signature_parts: list[str] = []
    if params_name:
        signature_parts.append(f"params {params_name}")
    if op.request_schema:
        signature_parts.append(f"body {request_type}")
    signature_parts.append("format string")
    signature = ", ".join(signature_parts)
    lines.append(f"func (c *Client) {name}({signature}) ({response_type}, error) {{")
    lines.append(f"  path := \"{op.path}\"")
    for param in op.path_params:
        lines.append(
            f"  path = strings.ReplaceAll(path, \"{{{param.name}}}\", url.PathEscape(fmt.Sprint(params.{_pascal_case(param.name)})))"
        )
    lines.append("  query := url.Values{}")
    for param in op.query_params:
        field = _pascal_case(param.name)
        if param.required:
            lines.append(f"  query.Set(\"{param.name}\", fmt.Sprint(params.{field}))")
        else:
            lines.append(f"  if params.{field} != nil {{")
            lines.append(f"    query.Set(\"{param.name}\", fmt.Sprint(*params.{field}))")
            lines.append("  }")
    lines.append("  if format != \"\" {")
    lines.append("    query.Set(\"format\", format)")
    lines.append("  }")
    body_expr = "nil"
    if op.request_schema:
        body_expr = "body"
    lines.append(f"  data, err := c.doRequest(\"{op.method.upper()}\", path, query, {body_expr})")
    lines.append("  if err != nil {")
    lines.append(f"    var empty {response_type}")
    lines.append("    return empty, err")
    lines.append("  }")
    lines.append(f"  var out {response_type}")
    lines.append("  if format == \"toon\" {")
    lines.append("    decoded, err := decodeToon(strings.TrimSpace(string(data)))")
    lines.append("    if err != nil {")
    lines.append("      return out, err")
    lines.append("    }")
    lines.append("    data = decoded")
    lines.append("  }")
    lines.append("  if err := json.Unmarshal(data, &out); err != nil {")
    lines.append("    return out, err")
    lines.append("  }")
    lines.append("  return out, nil")
    lines.append("}")
    return lines


def _go_operation_type(schema: dict | None, components: dict[str, dict], default_name: str) -> str:
    if schema is None:
        return "Json"
    ref = _schema_ref_name(schema)
    if ref:
        return ref
    if _schema_is_object(schema):
        return default_name
    return _go_type_from_schema(schema, components)


def _go_module_name(spec: dict) -> str:
    title = (spec.get("info") or {}).get("title") or "namel3ss_sdk"
    slug = slugify_text(str(title)) or "namel3ss_sdk"
    return slug.replace("-", "_")


__all__ = ["generate_go_client"]
