from __future__ import annotations

import os
import sys
import threading
from dataclasses import dataclass
from http.server import HTTPServer, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.utils.simple_yaml import parse_yaml


CONCURRENCY_CONFIG_FILENAME = "concurrency.yaml"
DEFAULT_SERVER_MODE = "threaded"
DEFAULT_MAX_THREADS = 8
DEFAULT_WORKER_PROCESSES = 1


@dataclass(frozen=True)
class ConcurrencyConfig:
    server_mode: str
    max_threads: int
    worker_processes: int
    require_free_threaded: bool
    compiled_cache_enabled: bool
    python_version: str
    gil_enabled: bool | None

    @property
    def free_threaded(self) -> bool:
        return self.gil_enabled is False

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "server_mode": self.server_mode,
            "max_threads": int(self.max_threads),
            "worker_processes": int(self.worker_processes),
            "require_free_threaded": bool(self.require_free_threaded),
            "free_threaded": bool(self.free_threaded),
            "compiled_cache_enabled": bool(self.compiled_cache_enabled),
            "python_version": self.python_version,
        }
        if self.gil_enabled is None:
            payload["gil_enabled"] = "unknown"
        else:
            payload["gil_enabled"] = bool(self.gil_enabled)
        return payload


class DeterministicThreadingHTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(
        self,
        server_address: tuple[str, int],
        handler_class,
        *,
        max_threads: int,
    ) -> None:
        self.max_threads = max(1, int(max_threads))
        self._slots = threading.BoundedSemaphore(self.max_threads)
        super().__init__(server_address, handler_class)

    def process_request(self, request, client_address) -> None:
        self._slots.acquire()
        try:
            super().process_request(request, client_address)
        except Exception:
            self._slots.release()
            raise

    def process_request_thread(self, request, client_address) -> None:
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._slots.release()


def load_concurrency_config(
    *,
    project_root: Path | None = None,
    app_path: Path | None = None,
) -> ConcurrencyConfig:
    config_path = _config_path(project_root=project_root, app_path=app_path)
    payload = _read_payload(config_path)

    server_mode = _server_mode(payload.get("server_mode"), env_name="N3_SERVER_MODE")
    max_threads = _positive_int(
        payload.get("max_threads"),
        env_name="N3_MAX_THREADS",
        default=DEFAULT_MAX_THREADS,
        field_name="max_threads",
    )
    worker_processes = _positive_int(
        payload.get("worker_processes"),
        env_name="N3_WORKER_PROCESSES",
        default=DEFAULT_WORKER_PROCESSES,
        field_name="worker_processes",
    )
    require_free_threaded = _bool_value(
        payload.get("require_free_threaded"),
        env_name="N3_REQUIRE_FREE_THREADED",
        default=False,
        field_name="require_free_threaded",
    )
    compiled_cache_enabled = _bool_value(
        payload.get("compiled_cache_enabled"),
        env_name="N3_COMPILED_CACHE",
        default=True,
        field_name="compiled_cache_enabled",
    )

    gil_enabled = _detect_gil_enabled()
    if require_free_threaded and gil_enabled is not False:
        raise Namel3ssError(
            build_guidance_message(
                what="Free-threaded Python is required by concurrency configuration.",
                why="require_free_threaded is true, but this interpreter still reports GIL enabled or unknown.",
                fix="Use a free-threaded Python build, or set require_free_threaded to false.",
                example="require_free_threaded: false",
            )
        )

    return ConcurrencyConfig(
        server_mode=server_mode,
        max_threads=max_threads,
        worker_processes=worker_processes,
        require_free_threaded=require_free_threaded,
        compiled_cache_enabled=compiled_cache_enabled,
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        gil_enabled=gil_enabled,
    )


def create_runtime_http_server(
    host: str,
    port: int,
    handler_class,
    *,
    config: ConcurrencyConfig,
) -> HTTPServer:
    if config.server_mode == "single":
        return HTTPServer((host, int(port)), handler_class)
    return DeterministicThreadingHTTPServer(
        (host, int(port)),
        handler_class,
        max_threads=config.max_threads,
    )


def _config_path(*, project_root: Path | None, app_path: Path | None) -> Path | None:
    if project_root is not None:
        return Path(project_root).resolve() / CONCURRENCY_CONFIG_FILENAME
    if app_path is not None:
        return Path(app_path).resolve().parent / CONCURRENCY_CONFIG_FILENAME
    return None


def _read_payload(config_path: Path | None) -> dict[str, Any]:
    if config_path is None or not config_path.exists():
        return {}
    try:
        parsed = parse_yaml(config_path.read_text(encoding="utf-8"))
    except Exception as err:
        raise Namel3ssError(
            build_guidance_message(
                what="concurrency.yaml is invalid.",
                why=f"{config_path.as_posix()} could not be parsed: {err}.",
                fix="Fix concurrency.yaml values and retry.",
                example="server_mode: threaded",
            )
        ) from err
    if not isinstance(parsed, dict):
        raise Namel3ssError(
            build_guidance_message(
                what="concurrency.yaml must be a map.",
                why="Top-level values must be key-value settings.",
                fix="Use key-value fields like max_threads and worker_processes.",
                example="max_threads: 8",
            )
        )
    return parsed


def _server_mode(raw: object, *, env_name: str) -> str:
    value = _env_or_raw(env_name, raw)
    text = str(value if value is not None else DEFAULT_SERVER_MODE).strip().lower()
    if text in {"single", "threaded"}:
        return text
    raise Namel3ssError(
        build_guidance_message(
            what=f"Invalid server_mode '{text or '<empty>'}'.",
            why="Only single and threaded server modes are supported.",
            fix="Set server_mode to single or threaded.",
            example="server_mode: threaded",
        )
    )


def _positive_int(raw: object, *, env_name: str, default: int, field_name: str) -> int:
    value = _env_or_raw(env_name, raw)
    if value is None:
        return int(default)
    text = str(value).strip()
    try:
        number = int(text)
    except ValueError as err:
        raise Namel3ssError(
            build_guidance_message(
                what=f"Invalid {field_name} value '{text or '<empty>'}'.",
                why=f"{field_name} must be a positive integer.",
                fix=f"Set {field_name} to a number like {default}.",
                example=f"{field_name}: {default}",
            )
        ) from err
    if number < 1:
        raise Namel3ssError(
            build_guidance_message(
                what=f"Invalid {field_name} value '{number}'.",
                why=f"{field_name} must be at least 1.",
                fix=f"Set {field_name} to a value greater than 0.",
                example=f"{field_name}: {default}",
            )
        )
    return number


def _bool_value(raw: object, *, env_name: str, default: bool, field_name: str) -> bool:
    value = _env_or_raw(env_name, raw)
    if value is None:
        return bool(default)
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    raise Namel3ssError(
        build_guidance_message(
            what=f"Invalid {field_name} value '{text or '<empty>'}'.",
            why=f"{field_name} must be true or false.",
            fix=f"Set {field_name} to true or false.",
            example=f"{field_name}: {str(default).lower()}",
        )
    )


def _env_or_raw(env_name: str, raw: object) -> object:
    env_value = os.getenv(env_name)
    if env_value is not None and env_value.strip() != "":
        return env_value
    return raw


def _detect_gil_enabled() -> bool | None:
    probe = getattr(sys, "_is_gil_enabled", None)
    if callable(probe):
        try:
            value = probe()
            if isinstance(value, bool):
                return value
        except Exception:
            return None
    return None


__all__ = [
    "CONCURRENCY_CONFIG_FILENAME",
    "DEFAULT_MAX_THREADS",
    "DEFAULT_SERVER_MODE",
    "DEFAULT_WORKER_PROCESSES",
    "ConcurrencyConfig",
    "DeterministicThreadingHTTPServer",
    "create_runtime_http_server",
    "load_concurrency_config",
]
