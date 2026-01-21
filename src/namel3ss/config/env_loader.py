from __future__ import annotations

import json
import os

from namel3ss.config.model import AppConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message


ENV_IDENTITY_JSON = "N3_IDENTITY_JSON"
ENV_IDENTITY_PREFIX = "N3_IDENTITY_"
ENV_AUTH_SIGNING_KEY = "N3_AUTH_SIGNING_KEY"
ENV_AUTH_ALLOW_IDENTITY = "N3_AUTH_ALLOW_IDENTITY"
ENV_AUTH_USERNAME = "N3_AUTH_USERNAME"
ENV_AUTH_PASSWORD = "N3_AUTH_PASSWORD"
ENV_AUTH_IDENTITY_JSON = "N3_AUTH_IDENTITY_JSON"
ENV_AUTH_CREDENTIALS_JSON = "N3_AUTH_CREDENTIALS_JSON"
RESERVED_TRUE_VALUES = {"1", "true", "yes", "on"}


def apply_env_overrides(config: AppConfig) -> bool:
    used = False
    host = os.getenv("NAMEL3SS_OLLAMA_HOST")
    if host:
        config.ollama.host = host
        used = True
    timeout = os.getenv("NAMEL3SS_OLLAMA_TIMEOUT_SECONDS")
    if timeout:
        try:
            config.ollama.timeout_seconds = int(timeout)
        except ValueError as err:
            raise Namel3ssError("NAMEL3SS_OLLAMA_TIMEOUT_SECONDS must be an integer") from err
        used = True
    api_key = os.getenv("NAMEL3SS_OPENAI_API_KEY")
    if api_key:
        config.openai.api_key = api_key
        used = True
    base_url = os.getenv("NAMEL3SS_OPENAI_BASE_URL")
    if base_url:
        config.openai.base_url = base_url
        used = True
    anthropic_key = os.getenv("NAMEL3SS_ANTHROPIC_API_KEY")
    if anthropic_key:
        config.anthropic.api_key = anthropic_key
        used = True
    gemini_key = os.getenv("NAMEL3SS_GEMINI_API_KEY")
    if gemini_key:
        config.gemini.api_key = gemini_key
        used = True
    mistral_key = os.getenv("NAMEL3SS_MISTRAL_API_KEY")
    if mistral_key:
        config.mistral.api_key = mistral_key
        used = True
    target = os.getenv("N3_PERSIST_TARGET")
    if target:
        config.persistence.target = normalize_target(target)
        used = True
    elif persist_enabled():
        config.persistence.target = "sqlite"
        used = True
    db_path = os.getenv("N3_DB_PATH")
    if db_path:
        config.persistence.db_path = db_path
        used = True
    database_url = os.getenv("N3_DATABASE_URL")
    if database_url:
        config.persistence.database_url = database_url
        used = True
    edge_kv_url = os.getenv("N3_EDGE_KV_URL")
    if edge_kv_url:
        config.persistence.edge_kv_url = edge_kv_url
        used = True
    replica_urls = os.getenv("N3_REPLICA_URLS")
    if replica_urls:
        values = [item.strip() for item in replica_urls.split(",")]
        config.persistence.replica_urls = [item for item in values if item]
        used = True
    tool_timeout = os.getenv("N3_PYTHON_TOOL_TIMEOUT_SECONDS")
    if tool_timeout:
        try:
            config.python_tools.timeout_seconds = int(tool_timeout)
        except ValueError as err:
            raise Namel3ssError("N3_PYTHON_TOOL_TIMEOUT_SECONDS must be an integer") from err
        used = True
    service_url = os.getenv("N3_TOOL_SERVICE_URL")
    if service_url:
        config.python_tools.service_url = service_url
        used = True
    foreign_strict = os.getenv("N3_FOREIGN_STRICT")
    if foreign_strict is not None:
        config.foreign.strict = foreign_strict.strip().lower() in RESERVED_TRUE_VALUES
        used = True
    foreign_allow = os.getenv("N3_FOREIGN_ALLOW")
    if foreign_allow is not None:
        config.foreign.allow = foreign_allow.strip().lower() in RESERVED_TRUE_VALUES
        used = True
    used = apply_authentication_env(config) or used
    used = apply_identity_env(config) or used
    return used


def apply_identity_env(config: AppConfig) -> bool:
    used = False
    identity_json = os.getenv(ENV_IDENTITY_JSON)
    if identity_json:
        try:
            parsed = json.loads(identity_json)
        except json.JSONDecodeError as err:
            raise Namel3ssError(_identity_json_error(str(err))) from err
        if not isinstance(parsed, dict):
            raise Namel3ssError(_identity_json_error("Expected a JSON object"))
        config.identity.defaults = dict(parsed)
        return True
    for key, value in os.environ.items():
        if not key.startswith(ENV_IDENTITY_PREFIX) or key == ENV_IDENTITY_JSON:
            continue
        field = key[len(ENV_IDENTITY_PREFIX):].lower()
        if not field:
            continue
        config.identity.defaults[field] = value
        used = True
    return used


def apply_authentication_env(config: AppConfig) -> bool:
    used = False
    signing_key = os.getenv(ENV_AUTH_SIGNING_KEY)
    if signing_key:
        config.authentication.signing_key = signing_key
        used = True
    allow_identity = os.getenv(ENV_AUTH_ALLOW_IDENTITY)
    if allow_identity is not None:
        config.authentication.allow_identity = allow_identity.strip().lower() in RESERVED_TRUE_VALUES
        used = True
    username = os.getenv(ENV_AUTH_USERNAME)
    if username:
        config.authentication.username = username
        used = True
    password = os.getenv(ENV_AUTH_PASSWORD)
    if password:
        config.authentication.password = password
        used = True
    identity_json = os.getenv(ENV_AUTH_IDENTITY_JSON)
    if identity_json:
        parsed = _parse_auth_json(identity_json, ENV_AUTH_IDENTITY_JSON)
        if not isinstance(parsed, dict):
            raise Namel3ssError(_auth_json_error(ENV_AUTH_IDENTITY_JSON, "Expected a JSON object"))
        config.authentication.identity = dict(parsed)
        used = True
    credentials_json = os.getenv(ENV_AUTH_CREDENTIALS_JSON)
    if credentials_json:
        parsed = _parse_auth_json(credentials_json, ENV_AUTH_CREDENTIALS_JSON)
        if not isinstance(parsed, dict):
            raise Namel3ssError(_auth_json_error(ENV_AUTH_CREDENTIALS_JSON, "Expected a JSON object"))
        username = parsed.get("username")
        password = parsed.get("password")
        identity = parsed.get("identity")
        if username is not None:
            config.authentication.username = str(username)
        if password is not None:
            config.authentication.password = str(password)
        if isinstance(identity, dict):
            config.authentication.identity = dict(identity)
        used = True
    return used


def normalize_target(raw: str) -> str:
    normalized = raw.strip().lower()
    if normalized in {"memory", "mem", "none", "off"}:
        return "memory"
    if normalized in {"sqlite", "postgres", "mysql", "edge"}:
        return normalized
    raise Namel3ssError(
        build_guidance_message(
            what=f"Unsupported persistence target '{raw}'.",
            why="Targets must be one of sqlite, postgres, mysql, edge, or memory.",
            fix="Set N3_PERSIST_TARGET to a supported value.",
            example="N3_PERSIST_TARGET=sqlite",
        )
    )


def persist_enabled() -> bool:
    value = os.getenv("N3_PERSIST", "").strip().lower()
    return value in RESERVED_TRUE_VALUES


def _identity_json_error(details: str) -> str:
    return build_guidance_message(
        what="Identity JSON is invalid.",
        why=f"Parsing N3_IDENTITY_JSON failed: {details}.",
        fix="Provide a valid JSON object for identity defaults.",
        example='N3_IDENTITY_JSON={"email":"dev@example.com","role":"admin"}',
    )


def _auth_json_error(label: str, details: str) -> str:
    return build_guidance_message(
        what=f"{label} is invalid.",
        why=f"Parsing {label} failed: {details}.",
        fix="Provide a valid JSON object for authentication settings.",
        example=f'{label}={{"username":"dev","password":"dev","identity":{{"role":"admin"}}}}',
    )


def _parse_auth_json(value: str, label: str) -> dict:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as err:
        raise Namel3ssError(_auth_json_error(label, str(err))) from err
    if not isinstance(parsed, dict):
        raise Namel3ssError(_auth_json_error(label, "Expected a JSON object"))
    return parsed


__all__ = [
    "ENV_IDENTITY_JSON",
    "ENV_IDENTITY_PREFIX",
    "ENV_AUTH_SIGNING_KEY",
    "ENV_AUTH_ALLOW_IDENTITY",
    "ENV_AUTH_USERNAME",
    "ENV_AUTH_PASSWORD",
    "ENV_AUTH_IDENTITY_JSON",
    "ENV_AUTH_CREDENTIALS_JSON",
    "RESERVED_TRUE_VALUES",
    "apply_env_overrides",
    "normalize_target",
]
