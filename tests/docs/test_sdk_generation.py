from __future__ import annotations

from namel3ss.docs.sdk import (
    generate_go_client,
    generate_python_client,
    generate_rust_client,
    generate_typescript_client,
    generate_postman_collection,
)


def test_sdk_generation_outputs() -> None:
    spec = {
        "openapi": "3.0.3",
        "info": {"title": "demo", "version": "1.0"},
        "paths": {
            "/api/users": {
                "get": {
                    "operationId": "list_users",
                    "parameters": [
                        {"name": "page", "in": "query", "required": False, "schema": {"type": "number"}}
                    ],
                }
            },
            "/api/users/{id}": {
                "post": {
                    "operationId": "create_user",
                    "parameters": [
                        {"name": "id", "in": "path", "required": True, "schema": {"type": "number"}}
                    ],
                    "requestBody": {"required": True, "content": {"application/json": {"schema": {"type": "object"}}}},
                }
            },
        },
        "components": {"schemas": {}},
    }
    python_client = generate_python_client(spec)
    expected_python = """from __future__ import annotations

from typing import Any, Dict, Optional
import base64
import json
import requests


class ApiError(Exception):
    def __init__(self, code: str, message: str, remediation: str, status: int) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message
        self.remediation = remediation
        self.status = status


def _decode_toon(token: str) -> Dict[str, Any]:
    padded = token + "=" * ((4 - len(token) % 4) % 4)
    raw = base64.urlsafe_b64decode(padded.encode("ascii"))
    return json.loads(raw.decode("utf-8")) if raw else {}


def _raise_api_error(response: requests.Response) -> None:
    try:
        payload = response.json()
    except Exception:
        raise ApiError("http_error", f"Request failed with {response.status_code}", "Check the request and try again.", response.status_code)
    code = str(payload.get("code") or "http_error")
    message = str(payload.get("message") or "Request failed")
    remediation = str(payload.get("remediation") or "Check the request and try again.")
    raise ApiError(code, message, remediation, response.status_code)


class Client:
    def __init__(self, base_url: str = "http://127.0.0.1:7340") -> None:
        self.base_url = base_url.rstrip('/')

    def create_user(
        self,
        *,
        path: Optional[Dict[str, Any]] = None,
        query: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None,
        format: Optional[str] = None,
    ) -> Dict[str, Any]:
        path_params = path or {}
        url = self.base_url + "/api/users/{id}".format(**path_params)
        params = query or {}
        if format:
            params["format"] = format
        response = requests.post(url, params=params, json=body)
        if not response.ok:
            _raise_api_error(response)
        if format == "toon":
            return _decode_toon(response.text)
        return response.json()

    def list_users(
        self,
        *,
        path: Optional[Dict[str, Any]] = None,
        query: Optional[Dict[str, Any]] = None,
        format: Optional[str] = None,
    ) -> Dict[str, Any]:
        path_params = path or {}
        url = self.base_url + "/api/users".format(**path_params)
        params = query or {}
        if format:
            params["format"] = format
        response = requests.get(url, params=params)
        if not response.ok:
            _raise_api_error(response)
        if format == "toon":
            return _decode_toon(response.text)
        return response.json()
"""
    assert python_client == expected_python
    typescript_client = generate_typescript_client(spec)
    expected_ts = """export type Json = Record<string, unknown>;
export type ErrorEnvelope = { code: string; message: string; remediation: string };

export class ApiError extends Error {
  code: string;
  remediation: string;
  status: number;
  constructor(envelope: ErrorEnvelope, status: number) {
    super(`${envelope.code}: ${envelope.message}`);
    this.code = envelope.code;
    this.remediation = envelope.remediation;
    this.status = status;
  }
}

function decodeToon(token: string): Json {
  const pad = "=".repeat((4 - (token.length % 4)) % 4);
  const padded = token + pad;
  let raw = "";
  if (typeof Buffer !== "undefined") {
    raw = Buffer.from(padded, "base64").toString("utf-8");
  } else if (typeof atob !== "undefined") {
    raw = atob(padded);
  }
  return raw ? (JSON.parse(raw) as Json) : {};
}

export class Client {
  private baseUrl: string = "http://127.0.0.1:7340";

  constructor(baseUrl?: string) {
    if (baseUrl) {
      this.baseUrl = baseUrl.replace(/\\/$/, "");
    }
  }

  async createUser(path: Record<string, unknown> = {}, query: Record<string, unknown> = {}, body?: Json, format?: string): Promise<Json> {
    const pathTemplate = "/api/users/{id}";
    const renderedPath = pathTemplate.replace(/\\{(\\w+)\\}/g, (_, key) => String(path[key]));
    const url = new URL(this.baseUrl + renderedPath);
    if (format) {
      query["format"] = format;
    }
    Object.entries(query).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        url.searchParams.append(key, String(value));
      }
    });
    const headers: Record<string, string> = {};
    headers["Content-Type"] = "application/json";
    const response = await fetch(url.toString(), {
      method: "POST",
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!response.ok) {
      let envelope: ErrorEnvelope = { code: "http_error", message: "Request failed", remediation: "Check the request and try again." };
      try {
        envelope = (await response.json()) as ErrorEnvelope;
      } catch {
        // ignore parsing failures
      }
      throw new ApiError(envelope, response.status);
    }
    if (format === "toon") {
      const text = await response.text();
      return decodeToon(text);
    }
    return response.json() as Promise<Json>;
  }

  async listUsers(path: Record<string, unknown> = {}, query: Record<string, unknown> = {}, body?: Json, format?: string): Promise<Json> {
    const pathTemplate = "/api/users";
    const renderedPath = pathTemplate.replace(/\\{(\\w+)\\}/g, (_, key) => String(path[key]));
    const url = new URL(this.baseUrl + renderedPath);
    if (format) {
      query["format"] = format;
    }
    Object.entries(query).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        url.searchParams.append(key, String(value));
      }
    });
    const headers: Record<string, string> = {};
    const response = await fetch(url.toString(), {
      method: "GET",
      headers,
    });
    if (!response.ok) {
      let envelope: ErrorEnvelope = { code: "http_error", message: "Request failed", remediation: "Check the request and try again." };
      try {
        envelope = (await response.json()) as ErrorEnvelope;
      } catch {
        // ignore parsing failures
      }
      throw new ApiError(envelope, response.status);
    }
    if (format === "toon") {
      const text = await response.text();
      return decodeToon(text);
    }
    return response.json() as Promise<Json>;
  }

}
"""
    assert typescript_client == expected_ts
    postman = generate_postman_collection(spec)
    expected_postman = {
        "info": {
            "name": "demo",
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "item": [
            {
                "name": "create_user",
                "request": {
                    "method": "POST",
                    "header": [{"key": "Content-Type", "value": "application/json"}],
                    "url": {
                        "raw": "{{base_url}}/api/users/{id}",
                        "host": ["{{base_url}}"],
                        "path": ["api", "users", "{id}"],
                        "query": [],
                    },
                    "body": {"mode": "raw", "raw": "{}"},
                },
            },
            {
                "name": "list_users",
                "request": {
                    "method": "GET",
                    "header": [{"key": "Content-Type", "value": "application/json"}],
                    "url": {
                        "raw": "{{base_url}}/api/users",
                        "host": ["{{base_url}}"],
                        "path": ["api", "users"],
                        "query": [{"key": "page", "value": ""}],
                    },
                },
            },
        ],
    }
    assert postman == expected_postman
    go_files = generate_go_client(spec)
    expected_go = {
        "client.go": """package namel3ss

import (
  "bytes"
  "encoding/base64"
  "encoding/json"
  "fmt"
  "io"
  "net/http"
  "net/url"
  "strings"
)

type Json map[string]any

type ErrorEnvelope struct {
  Code string `json:"code"`
  Message string `json:"message"`
  Remediation string `json:"remediation"`
}

type ApiError struct {
  Status int
  Envelope ErrorEnvelope
}

func (e ApiError) Error() string {
  return fmt.Sprintf("%s: %s", e.Envelope.Code, e.Envelope.Message)
}

type CreateUserParams struct {
  Id float64 `json:"id"`
}

type ListUsersParams struct {
  Page *float64 `json:"page,omitempty"`
}


type Client struct {
  BaseURL string
  HTTPClient *http.Client
}

func NewClient(baseURL string) *Client {
  if strings.TrimSpace(baseURL) == "" {
    baseURL = "http://127.0.0.1:7340"
  }
  return &Client{BaseURL: strings.TrimRight(baseURL, "/"), HTTPClient: &http.Client{}}
}

func decodeToon(token string) ([]byte, error) {
  padded := token + strings.Repeat("=", (4 - (len(token) % 4)) % 4)
  raw, err := base64.URLEncoding.DecodeString(padded)
  if err != nil {
    return nil, err
  }
  return raw, nil
}

func (c *Client) doRequest(method string, path string, query url.Values, body any) ([]byte, error) {
  urlStr := c.BaseURL + path
  if len(query) > 0 {
    urlStr = urlStr + "?" + query.Encode()
  }
  var reader io.Reader
  if body != nil {
    raw, err := json.Marshal(body)
    if err != nil {
      return nil, err
    }
    reader = bytes.NewReader(raw)
  }
  req, err := http.NewRequest(method, urlStr, reader)
  if err != nil {
    return nil, err
  }
  if body != nil {
    req.Header.Set("Content-Type", "application/json")
  }
  client := c.HTTPClient
  if client == nil {
    client = &http.Client{}
  }
  resp, err := client.Do(req)
  if err != nil {
    return nil, err
  }
  defer resp.Body.Close()
  data, err := io.ReadAll(resp.Body)
  if err != nil {
    return nil, err
  }
  if resp.StatusCode >= 400 {
    env := ErrorEnvelope{Code: "http_error", Message: "Request failed", Remediation: "Check the request and try again."}
    _ = json.Unmarshal(data, &env)
    return nil, ApiError{Status: resp.StatusCode, Envelope: env}
  }
  return data, nil
}

func (c *Client) CreateUser(params CreateUserParams, body map[string]any, format string) (Json, error) {
  path := "/api/users/{id}"
  path = strings.ReplaceAll(path, "{id}", url.PathEscape(fmt.Sprint(params.Id)))
  query := url.Values{}
  if format != "" {
    query.Set("format", format)
  }
  data, err := c.doRequest("POST", path, query, body)
  if err != nil {
    var empty Json
    return empty, err
  }
  var out Json
  if format == "toon" {
    decoded, err := decodeToon(strings.TrimSpace(string(data)))
    if err != nil {
      return out, err
    }
    data = decoded
  }
  if err := json.Unmarshal(data, &out); err != nil {
    return out, err
  }
  return out, nil
}

func (c *Client) ListUsers(params ListUsersParams, format string) (Json, error) {
  path := "/api/users"
  query := url.Values{}
  if params.Page != nil {
    query.Set("page", fmt.Sprint(*params.Page))
  }
  if format != "" {
    query.Set("format", format)
  }
  data, err := c.doRequest("GET", path, query, nil)
  if err != nil {
    var empty Json
    return empty, err
  }
  var out Json
  if format == "toon" {
    decoded, err := decodeToon(strings.TrimSpace(string(data)))
    if err != nil {
      return out, err
    }
    data = decoded
  }
  if err := json.Unmarshal(data, &out); err != nil {
    return out, err
  }
  return out, nil
}
""",
        "go.mod": """module demo

go 1.20
""",
    }
    assert go_files == expected_go
    rust_files = generate_rust_client(spec)
    expected_rust = {
        "Cargo.toml": """[package]
name = "demo"
version = "0.1.0"
edition = "2021"

[dependencies]
reqwest = { version = "0.11", features = ["json", "blocking"] }
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
base64 = "0.21"
urlencoding = "2.1"
""",
        "src/lib.rs": """use base64::engine::general_purpose::URL_SAFE;
use base64::Engine;
use reqwest::blocking::Client as HttpClient;
use serde::{Deserialize, Serialize};
use serde_json::Value;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ErrorEnvelope {
    pub code: String,
    pub message: String,
    pub remediation: String,
}

#[derive(Debug, Clone)]
pub struct ApiError {
    pub status: u16,
    pub envelope: ErrorEnvelope,
}

impl std::fmt::Display for ApiError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}: {}", self.envelope.code, self.envelope.message)
    }
}

impl std::error::Error for ApiError {}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CreateUserParams {
    #[serde(rename = "id")]
    pub id: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ListUsersParams {
    #[serde(rename = "page")]
    pub page: Option<f64>,
}


#[derive(Debug, Clone)]
pub struct Client {
    base_url: String,
    http: HttpClient,
}

impl Client {
    pub fn new(base_url: Option<&str>) -> Self {
        let base = base_url.unwrap_or("http://127.0.0.1:7340").trim_end_matches('/').to_string();
        Self { base_url: base, http: HttpClient::new() }
    }

    fn decode_toon(&self, token: &str) -> Result<Value, ApiError> {
        let pad = "=".repeat((4 - (token.len() % 4)) % 4);
        let padded = format!("{}{}", token, pad);
        let raw = URL_SAFE.decode(padded.as_bytes()).unwrap_or_default();
        let value: Value = serde_json::from_slice(&raw).unwrap_or(Value::Null);
        Ok(value)
    }

    pub fn create_user(&self, params: CreateUserParams, body: Value, format: Option<&str>) -> Result<Value, ApiError> {
        let mut path = "/api/users/{id}".to_string();
        path = path.replace("{id}", &urlencoding::encode(&params.id.to_string()));
        let mut query: Vec<(String, String)> = Vec::new();
        if let Some(fmt_value) = format {
            query.push(("format".to_string(), fmt_value.to_string()));
        }
        let url = format!("{}{}", self.base_url, path);
        let mut request = self.http.request(reqwest::Method::from_bytes(b"POST").unwrap(), &url);
        if !query.is_empty() {
            request = request.query(&query);
        }
        request = request.json(&body);
        let response = request.send();
        if response.is_err() {
            return Err(ApiError { status: 0, envelope: ErrorEnvelope { code: "http_error".to_string(), message: "Request failed".to_string(), remediation: "Check the request and try again.".to_string() } });
        }
        let response = response.unwrap();
        let status = response.status().as_u16();
        let text = response.text().unwrap_or_default();
        if status >= 400 {
            let envelope: ErrorEnvelope = serde_json::from_str(&text).unwrap_or(ErrorEnvelope { code: "http_error".to_string(), message: "Request failed".to_string(), remediation: "Check the request and try again.".to_string() });
            return Err(ApiError { status, envelope });
        }
        if let Some(fmt_value) = format {
            if fmt_value == "toon" {
                let decoded = self.decode_toon(&text)?;
                let parsed: Result<Value, _> = serde_json::from_value(decoded);
                if let Ok(out) = parsed {
                    return Ok(out);
                }
                let envelope = ErrorEnvelope { code: "decode_error".to_string(), message: "Response decode failed".to_string(), remediation: "Check the response format.".to_string() };
                return Err(ApiError { status: 200, envelope });
            }
        }
        let parsed: Result<Value, _> = serde_json::from_str(&text);
        if let Ok(out) = parsed {
            return Ok(out);
        }
        let envelope = ErrorEnvelope { code: "decode_error".to_string(), message: "Response decode failed".to_string(), remediation: "Check the response format.".to_string() };
        Err(ApiError { status: 200, envelope })
    }

    pub fn list_users(&self, params: ListUsersParams, format: Option<&str>) -> Result<Value, ApiError> {
        let mut path = "/api/users".to_string();
        let mut query: Vec<(String, String)> = Vec::new();
        if let Some(value) = &params.page {
            query.push(("page".to_string(), value.to_string()));
        }
        if let Some(fmt_value) = format {
            query.push(("format".to_string(), fmt_value.to_string()));
        }
        let url = format!("{}{}", self.base_url, path);
        let mut request = self.http.request(reqwest::Method::from_bytes(b"GET").unwrap(), &url);
        if !query.is_empty() {
            request = request.query(&query);
        }
        let response = request.send();
        if response.is_err() {
            return Err(ApiError { status: 0, envelope: ErrorEnvelope { code: "http_error".to_string(), message: "Request failed".to_string(), remediation: "Check the request and try again.".to_string() } });
        }
        let response = response.unwrap();
        let status = response.status().as_u16();
        let text = response.text().unwrap_or_default();
        if status >= 400 {
            let envelope: ErrorEnvelope = serde_json::from_str(&text).unwrap_or(ErrorEnvelope { code: "http_error".to_string(), message: "Request failed".to_string(), remediation: "Check the request and try again.".to_string() });
            return Err(ApiError { status, envelope });
        }
        if let Some(fmt_value) = format {
            if fmt_value == "toon" {
                let decoded = self.decode_toon(&text)?;
                let parsed: Result<Value, _> = serde_json::from_value(decoded);
                if let Ok(out) = parsed {
                    return Ok(out);
                }
                let envelope = ErrorEnvelope { code: "decode_error".to_string(), message: "Response decode failed".to_string(), remediation: "Check the response format.".to_string() };
                return Err(ApiError { status: 200, envelope });
            }
        }
        let parsed: Result<Value, _> = serde_json::from_str(&text);
        if let Ok(out) = parsed {
            return Ok(out);
        }
        let envelope = ErrorEnvelope { code: "decode_error".to_string(), message: "Response decode failed".to_string(), remediation: "Check the response format.".to_string() };
        Err(ApiError { status: 200, envelope })
    }
}
""",
    }
    assert rust_files == expected_rust
