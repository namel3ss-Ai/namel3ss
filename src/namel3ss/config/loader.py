from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

from namel3ss.config.dotenv import apply_dotenv, load_dotenv_for_path
from namel3ss.config.env_loader import apply_env_overrides, normalize_target
from namel3ss.config.model import AppConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
CONFIG_FILENAME = "namel3ss.toml"
@dataclass(frozen=True)
class ConfigSource:
    kind: str
    path: str | None = None

def load_config(app_path: Path | None = None, root: Path | None = None) -> AppConfig:
    config, _ = resolve_config(app_path=app_path, root=root)
    return config
def resolve_config(
    app_path: Path | None = None,
    root: Path | None = None,
) -> tuple[AppConfig, list[ConfigSource]]:
    config = AppConfig()
    sources: list[ConfigSource] = []
    project_root = _resolve_root(app_path, root)
    if project_root:
        toml_path = project_root / CONFIG_FILENAME
        if toml_path.exists():
            data = _parse_toml(toml_path.read_text(encoding="utf-8"), toml_path)
            _apply_toml_config(config, data)
            sources.append(ConfigSource(kind="toml", path=toml_path.as_posix()))
        env_path = project_root / ".env"
        if env_path.exists():
            apply_dotenv(load_dotenv_for_path(str(env_path)))
            sources.append(ConfigSource(kind="dotenv", path=env_path.as_posix()))
    elif app_path:
        env_path = Path(app_path).resolve().parent / ".env"
        if env_path.exists():
            apply_dotenv(load_dotenv_for_path(str(app_path)))
            sources.append(ConfigSource(kind="dotenv", path=env_path.as_posix()))
    if apply_env_overrides(config):
        sources.append(ConfigSource(kind="env", path=None))
    return config, sources
def _resolve_root(app_path: Path | None, root: Path | None) -> Path | None:
    if root:
        return Path(root).resolve()
    if app_path:
        return Path(app_path).resolve().parent
    return None

def _apply_toml_config(config: AppConfig, data: Dict[str, Any]) -> None:
    if not isinstance(data, dict):
        return
    _apply_ollama_toml(config, data.get("ollama"))
    _apply_provider_toml(config, data.get("openai"), provider="openai")
    _apply_provider_toml(config, data.get("anthropic"), provider="anthropic")
    _apply_provider_toml(config, data.get("gemini"), provider="gemini")
    _apply_provider_toml(config, data.get("mistral"), provider="mistral")
    _apply_answer_toml(config, data.get("answer"))
    _apply_embedding_toml(config, data.get("embedding"))
    _apply_persistence_toml(config, data.get("persistence"))
    _apply_identity_toml(config, data.get("identity"))
    _apply_authentication_toml(config, data.get("authentication") or data.get("auth"))
    _apply_python_tools_toml(config, data.get("python_tools") or data.get("python"))
    _apply_foreign_toml(config, data.get("foreign"))
    _apply_tool_packs_toml(config, data.get("tool_packs") or data.get("packs"))
    _apply_memory_packs_toml(config, data.get("memory_packs"))
    _apply_performance_toml(config, data.get("performance"))
    _apply_determinism_toml(config, data.get("determinism"))
    _apply_registries_toml(config, data.get("registries"))
    _apply_capability_overrides_toml(config, data.get("capability_overrides"))

def _apply_ollama_toml(config: AppConfig, table: Any) -> None:
    if not isinstance(table, dict):
        return
    host = table.get("host")
    if host is not None:
        config.ollama.host = str(host)
    timeout = table.get("timeout_seconds")
    if timeout is not None:
        try:
            config.ollama.timeout_seconds = int(timeout)
        except (TypeError, ValueError) as err:
            raise Namel3ssError("ollama.timeout_seconds must be an integer") from err

def _apply_provider_toml(config: AppConfig, table: Any, *, provider: str) -> None:
    if not isinstance(table, dict):
        return
    api_key = table.get("api_key")
    if api_key is not None:
        setattr(getattr(config, provider), "api_key", str(api_key))
    if provider == "openai":
        base_url = table.get("base_url")
        if base_url is not None:
            config.openai.base_url = str(base_url)
def _apply_answer_toml(config: AppConfig, table: Any) -> None:
    if not isinstance(table, dict):
        return
    provider = table.get("provider")
    if provider is not None:
        config.answer.provider = str(provider)
    model = table.get("model")
    if model is not None:
        config.answer.model = str(model)

def _apply_embedding_toml(config: AppConfig, table: Any) -> None:
    if not isinstance(table, dict):
        return
    provider = table.get("provider")
    if provider is not None:
        config.embedding.provider = str(provider)
    model = table.get("model")
    if model is not None:
        config.embedding.model = str(model)
    version = table.get("version")
    if version is not None:
        config.embedding.version = str(version)
    dims = table.get("dims")
    if dims is not None:
        try:
            config.embedding.dims = int(dims)
        except (TypeError, ValueError) as err:
            raise Namel3ssError("embedding.dims must be an integer") from err
    precision = table.get("precision")
    if precision is not None:
        try:
            config.embedding.precision = int(precision)
        except (TypeError, ValueError) as err:
            raise Namel3ssError("embedding.precision must be an integer") from err
    candidate_limit = table.get("candidate_limit") or table.get("candidate_max")
    if candidate_limit is not None:
        try:
            config.embedding.candidate_limit = int(candidate_limit)
        except (TypeError, ValueError) as err:
            raise Namel3ssError("embedding.candidate_limit must be an integer") from err
def _apply_persistence_toml(config: AppConfig, table: Any) -> None:
    if not isinstance(table, dict):
        return
    target = table.get("target")
    if target is not None:
        config.persistence.target = normalize_target(str(target))
    db_path = table.get("db_path")
    if db_path is not None:
        config.persistence.db_path = str(db_path)
    database_url = table.get("database_url")
    if database_url is not None:
        config.persistence.database_url = str(database_url)
    edge_kv_url = table.get("edge_kv_url")
    if edge_kv_url is not None:
        config.persistence.edge_kv_url = str(edge_kv_url)
    replicas = table.get("replicas")
    if replicas is None:
        replicas = table.get("replica_urls")
    if replicas is not None:
        if isinstance(replicas, list):
            config.persistence.replica_urls = [str(item) for item in replicas if item is not None]
        else:
            config.persistence.replica_urls = [str(replicas)]
def _apply_identity_toml(config: AppConfig, table: Any) -> None:
    if not isinstance(table, dict):
        return
    for key, value in table.items():
        if value is None:
            continue
        config.identity.defaults[str(key)] = value
def _apply_authentication_toml(config: AppConfig, table: Any) -> None:
    if not isinstance(table, dict):
        return
    signing_key = table.get("signing_key")
    if signing_key is not None:
        config.authentication.signing_key = str(signing_key)
    allow_identity = table.get("allow_identity")
    if allow_identity is not None:
        if not isinstance(allow_identity, bool):
            raise Namel3ssError("authentication.allow_identity must be true or false")
        config.authentication.allow_identity = allow_identity
    username = table.get("username")
    if username is not None:
        config.authentication.username = str(username)
    password = table.get("password")
    if password is not None:
        config.authentication.password = str(password)
    credentials = table.get("credentials")
    if isinstance(credentials, dict):
        _apply_authentication_credentials(config, credentials, label="authentication.credentials")
    identity = table.get("identity")
    if isinstance(identity, dict):
        config.authentication.identity = dict(identity)
    elif isinstance(identity, str):
        config.authentication.identity = _parse_auth_identity_json(identity, label="authentication.identity")
    identity_json = table.get("identity_json")
    if identity_json is not None:
        if not isinstance(identity_json, str):
            raise Namel3ssError("authentication.identity_json must be a JSON string")
        config.authentication.identity = _parse_auth_identity_json(identity_json, label="authentication.identity_json")
    credentials_json = table.get("credentials_json")
    if credentials_json is not None:
        if not isinstance(credentials_json, str):
            raise Namel3ssError("authentication.credentials_json must be a JSON string")
        parsed = _parse_auth_identity_json(credentials_json, label="authentication.credentials_json")
        if not isinstance(parsed, dict):
            raise Namel3ssError("authentication.credentials_json must be a JSON object")
        _apply_authentication_credentials(config, parsed, label="authentication.credentials_json")

def _apply_authentication_credentials(config: AppConfig, payload: dict, *, label: str) -> None:
    username = payload.get("username")
    password = payload.get("password")
    identity = payload.get("identity")
    if username is not None:
        config.authentication.username = str(username)
    if password is not None:
        config.authentication.password = str(password)
    if isinstance(identity, dict):
        config.authentication.identity = dict(identity)
    elif identity is not None:
        config.authentication.identity = _parse_auth_identity_json(identity, label=f"{label}.identity")
def _parse_auth_identity_json(value: object, *, label: str) -> dict:
    if isinstance(value, dict):
        return dict(value)
    if not isinstance(value, str):
        raise Namel3ssError(f"{label} must be a JSON object string")
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as err:
        raise Namel3ssError(
            build_guidance_message(
                what=f"{label} is not valid JSON.",
                why=f"JSON parsing failed: {err}.",
                fix="Provide a valid JSON object string.",
                example='identity_json = "{\\"role\\": \\"admin\\"}"',
            )
        ) from err
    if not isinstance(parsed, dict):
        raise Namel3ssError(f"{label} must be a JSON object string")
    return dict(parsed)
def _apply_python_tools_toml(config: AppConfig, table: Any) -> None:
    if not isinstance(table, dict):
        return
    timeout = table.get("timeout_seconds")
    if timeout is not None:
        try:
            config.python_tools.timeout_seconds = int(timeout)
        except (TypeError, ValueError) as err:
            raise Namel3ssError("python_tools.timeout_seconds must be an integer") from err
    service_url = table.get("service_url")
    if service_url is not None:
        config.python_tools.service_url = str(service_url)
    handshake_required = table.get("service_handshake_required")
    if handshake_required is not None:
        if not isinstance(handshake_required, bool):
            raise Namel3ssError("python_tools.service_handshake_required must be true or false")
        config.python_tools.service_handshake_required = handshake_required

def _apply_foreign_toml(config: AppConfig, table: Any) -> None:
    if not isinstance(table, dict):
        return
    strict = table.get("strict")
    if strict is not None:
        if not isinstance(strict, bool):
            raise Namel3ssError("foreign.strict must be true or false")
        config.foreign.strict = strict
    allow = table.get("allow")
    if allow is not None:
        if not isinstance(allow, bool):
            raise Namel3ssError("foreign.allow must be true or false")
        config.foreign.allow = allow

def _apply_tool_packs_toml(config: AppConfig, table: Any) -> None:
    if not isinstance(table, dict):
        return
    enabled = table.get("enabled_packs")
    if enabled is not None:
        config.tool_packs.enabled_packs = _ensure_str_list(enabled, "tool_packs.enabled_packs")
    disabled = table.get("disabled_packs")
    if disabled is not None:
        config.tool_packs.disabled_packs = _ensure_str_list(disabled, "tool_packs.disabled_packs")
    pinned = table.get("pinned_tools")
    if pinned is not None:
        config.tool_packs.pinned_tools = _ensure_str_map(pinned, "tool_packs.pinned_tools")

def _apply_memory_packs_toml(config: AppConfig, table: Any) -> None:
    if not isinstance(table, dict):
        return
    default_pack = table.get("default_pack") or table.get("default")
    if default_pack is not None:
        config.memory_packs.default_pack = str(default_pack)
    overrides = table.get("agent_overrides") or table.get("agent_packs") or table.get("agents")
    if overrides is not None:
        config.memory_packs.agent_overrides = _ensure_str_map(overrides, "memory_packs.agent_overrides")


def _apply_performance_toml(config: AppConfig, table: Any) -> None:
    if not isinstance(table, dict):
        return
    async_runtime = table.get("async_runtime")
    if async_runtime is not None:
        if not isinstance(async_runtime, bool):
            raise Namel3ssError("performance.async_runtime must be true or false")
        config.performance.async_runtime = async_runtime
    max_concurrency = table.get("max_concurrency")
    if max_concurrency is not None:
        try:
            value = int(max_concurrency)
        except (TypeError, ValueError) as err:
            raise Namel3ssError("performance.max_concurrency must be an integer") from err
        if value < 1:
            raise Namel3ssError("performance.max_concurrency must be >= 1")
        config.performance.max_concurrency = value
    cache_size = table.get("cache_size")
    if cache_size is not None:
        try:
            value = int(cache_size)
        except (TypeError, ValueError) as err:
            raise Namel3ssError("performance.cache_size must be an integer") from err
        if value < 0:
            raise Namel3ssError("performance.cache_size must be >= 0")
        config.performance.cache_size = value
    enable_batching = table.get("enable_batching")
    if enable_batching is not None:
        if not isinstance(enable_batching, bool):
            raise Namel3ssError("performance.enable_batching must be true or false")
        config.performance.enable_batching = enable_batching
    metrics_endpoint = table.get("metrics_endpoint")
    if metrics_endpoint is not None:
        config.performance.metrics_endpoint = str(metrics_endpoint)


def _apply_determinism_toml(config: AppConfig, table: Any) -> None:
    if not isinstance(table, dict):
        return
    seed = table.get("seed")
    if seed is None:
        config.determinism.seed = None
    elif isinstance(seed, bool):
        raise Namel3ssError("determinism.seed must be an integer, string, or null")
    elif isinstance(seed, int):
        if seed < 0:
            raise Namel3ssError("determinism.seed must be >= 0")
        config.determinism.seed = seed
    elif isinstance(seed, str):
        text = seed.strip()
        config.determinism.seed = text or None
    else:
        raise Namel3ssError("determinism.seed must be an integer, string, or null")
    explain = table.get("explain")
    if explain is not None:
        if not isinstance(explain, bool):
            raise Namel3ssError("determinism.explain must be true or false")
        config.determinism.explain = explain
    redact_user_data = table.get("redact_user_data")
    if redact_user_data is not None:
        if not isinstance(redact_user_data, bool):
            raise Namel3ssError("determinism.redact_user_data must be true or false")
        config.determinism.redact_user_data = redact_user_data


def _apply_registries_toml(config: AppConfig, table: Any) -> None:
    from namel3ss.config.model import RegistrySourceConfig, RegistriesConfig

    if not isinstance(table, dict):
        return
    sources = table.get("sources")
    default = table.get("default")
    parsed_sources: list[RegistrySourceConfig] = []
    if sources is not None:
        if not isinstance(sources, list):
            raise Namel3ssError("registries.sources must be a list of registry source entries")
        for raw in sources:
            if not isinstance(raw, dict):
                raise Namel3ssError("registries.sources entries must be tables")
            source_id = raw.get("id")
            kind = raw.get("kind")
            if not isinstance(source_id, str) or not source_id:
                raise Namel3ssError("registries.sources entries require id")
            if not isinstance(kind, str) or not kind:
                raise Namel3ssError("registries.sources entries require kind")
            parsed_sources.append(
                RegistrySourceConfig(
                    id=source_id,
                    kind=kind,
                    path=str(raw.get("path")) if raw.get("path") is not None else None,
                    url=str(raw.get("url")) if raw.get("url") is not None else None,
                )
            )
    parsed_default: list[str] = []
    if default is not None:
        parsed_default = _ensure_str_list(default, "registries.default")
    config.registries = RegistriesConfig(sources=parsed_sources, default=parsed_default)

def _apply_capability_overrides_toml(config: AppConfig, table: Any) -> None:
    if table is None:
        return
    if not isinstance(table, dict):
        raise Namel3ssError("capability_overrides must be a table mapping tool names to overrides")
    overrides: dict[str, dict[str, object]] = {}
    from namel3ss.runtime.capabilities.validate import normalize_overrides

    for key, value in table.items():
        if not isinstance(key, str) or not key:
            raise Namel3ssError("capability_overrides keys must be tool names")
        overrides[key] = normalize_overrides(value, label=f'"{key}"')
    config.capability_overrides = overrides

def _ensure_str_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise Namel3ssError(f"{label} must be a list of strings")
    return [str(item) for item in value]

def _ensure_str_map(value: Any, label: str) -> dict[str, str]:
    if not isinstance(value, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in value.items()):
        raise Namel3ssError(f"{label} must be a mapping of strings to strings")
    return {str(k): str(v) for k, v in value.items()}

def _parse_toml(text: str, path: Path) -> Dict[str, Any]:
    try:
        import tomllib  # type: ignore
    except Exception:
        return _parse_toml_minimal(text, path)
    try:
        data = tomllib.loads(text)
    except Exception as err:
        raise Namel3ssError(
            build_guidance_message(
                what="namel3ss.toml is not valid TOML.",
                why=f"TOML parsing failed: {err}.",
                fix="Fix the TOML syntax in namel3ss.toml.",
                example='[persistence]\\ntarget = "sqlite"',
            )
        ) from err
    return data if isinstance(data, dict) else {}

def _parse_toml_minimal(text: str, path: Path) -> Dict[str, Any]:
    current = None
    data: Dict[str, Any] = {}
    line_num = 0
    for raw_line in text.splitlines():
        line_num += 1
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].strip()
            data.setdefault(section, {})
            current = section
            continue
        if current is None:
            continue
        if "=" not in line:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Invalid line in {path.name}.",
                    why="Expected key = value inside a section.",
                    fix="Add a key/value entry under a section header.",
                    example='target = "sqlite"',
                ),
                line=line_num,
                column=1,
            )
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        data[current][key] = _parse_toml_value(value, line_num, path)
    return data

def _parse_toml_value(value: str, line_num: int, path: Path) -> Any:
    lowered = value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if value.startswith("[") and value.endswith("]"):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as err:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Unsupported array value in {path.name}.",
                    why=f"Array parsing failed: {err}.",
                    fix="Use a JSON-style array of strings.",
                    example='enabled_packs = ["pack.slug"]',
                ),
                line=line_num,
                column=1,
            ) from err
        if not isinstance(parsed, list) or any(not isinstance(item, str) for item in parsed):
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Unsupported array value in {path.name}.",
                    why="Only arrays of strings are supported.",
                    fix="Provide a list of quoted strings.",
                    example='enabled_packs = ["pack.slug"]',
                ),
                line=line_num,
                column=1,
            )
        return parsed
    if value.startswith("{") and value.endswith("}"):
        return _parse_inline_table(value, line_num, path)
    raise Namel3ssError(
        build_guidance_message(
            what=f"Unsupported value in {path.name}.",
            why="Only quoted strings, arrays of strings, and inline tables are supported.",
            fix="Wrap values in quotes, use arrays, or use inline tables.",
            example='enabled_packs = ["pack.slug"]',
        ),
        line=line_num,
        column=1,
    )

def _parse_inline_table(value: str, line_num: int, path: Path) -> Dict[str, Any]:
    inner = value[1:-1].strip()
    if not inner:
        return {}
    parts = _split_inline_parts(inner)
    table: Dict[str, Any] = {}
    for part in parts:
        if "=" not in part:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Inline table entry is invalid in {path.name}.",
                    why="Entries must be key = \"value\" pairs.",
                    fix="Add key/value pairs separated by commas.",
                    example='{ api_key = "token" }',
                ),
                line=line_num,
                column=1,
            )
        key, raw_value = part.split("=", 1)
        key = key.strip()
        raw_value = raw_value.strip()
        table[key] = _parse_toml_value(raw_value, line_num, path)
    return table

def _split_inline_parts(text: str) -> list[str]:
    parts: list[str] = []
    current = []
    in_string = False
    escape = False
    for ch in text:
        if escape:
            current.append(ch)
            escape = False
            continue
        if ch == "\\" and in_string:
            escape = True
            current.append(ch)
            continue
        if ch == '"':
            in_string = not in_string
            current.append(ch)
            continue
        if ch == "," and not in_string:
            part = "".join(current).strip()
            if part:
                parts.append(part)
            current = []
            continue
        current.append(ch)
    part = "".join(current).strip()
    if part:
        parts.append(part)
    return parts

__all__ = ["load_config", "resolve_config", "ConfigSource", "CONFIG_FILENAME"]
