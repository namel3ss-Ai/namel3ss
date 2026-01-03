from __future__ import annotations

import builtins
import contextlib
import io
import importlib
import os
import socket
import subprocess
from collections.abc import MutableMapping
from pathlib import Path
from urllib import request as urllib_request

from namel3ss.runtime.capabilities.gates import (
    check_env_read,
    check_env_write,
    check_filesystem,
    check_network,
    check_secret_allowed,
    check_subprocess,
)
from namel3ss.runtime.capabilities.gates.base import CapabilityViolation
from namel3ss.runtime.capabilities.model import CapabilityCheck, CapabilityContext
from namel3ss.runtime.capabilities.secrets import normalize_secret_name


_CONTEXT: CapabilityContext | None = None
_CHECKS: list[dict[str, object]] = []
_INSTALLED = False
_ORIGINALS: dict[str, object] = {}
_ENV_PROXY: "EnvProxy | None" = None


def configure(context: dict[str, object] | None) -> None:
    global _CONTEXT
    _CONTEXT = CapabilityContext.from_dict(context) if isinstance(context, dict) else None
    clear_checks()
    _install_patches()


def clear_checks() -> None:
    _CHECKS.clear()
    if _CONTEXT:
        _CONTEXT.allowed_emitted.clear()


def drain_checks() -> list[dict[str, object]]:
    output = list(_CHECKS)
    _CHECKS.clear()
    return output


def run(payload: dict) -> dict:
    protocol_version = payload.get("protocol_version", 1)
    entry = payload.get("entry")
    args = payload.get("payload")
    configure(payload.get("capability_context"))
    if not isinstance(entry, str):
        return _error_payload(ValueError("Missing entry"), protocol_version)
    try:
        module_path, function_name = entry.split(":", 1)
    except ValueError:
        return _error_payload(ValueError("Invalid entry"), protocol_version)
    try:
        module = importlib.import_module(module_path)
        func = getattr(module, function_name)
        if not callable(func):
            raise TypeError("Entry target is not callable")
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        with contextlib.redirect_stdout(stdout_buf), contextlib.redirect_stderr(stderr_buf):
            result = func(args)
        return {
            "ok": True,
            "result": result,
            "protocol_version": protocol_version,
            "capability_checks": drain_checks(),
        }
    except Exception as err:
        return _error_payload(err, protocol_version)


def _error_payload(err: Exception, protocol_version: int) -> dict:
    error = {"type": err.__class__.__name__, "message": str(err)}
    if isinstance(err, CapabilityViolation):
        reason = err.check.reason if err.check else None
        if isinstance(reason, str):
            error["reason_code"] = reason
    return {
        "ok": False,
        "error": error,
        "protocol_version": protocol_version,
        "capability_checks": drain_checks(),
    }


def _record_check(check: CapabilityCheck) -> None:
    if _CONTEXT is None:
        return
    if check.allowed and check.capability in _CONTEXT.allowed_emitted:
        return
    if check.allowed:
        _CONTEXT.allowed_emitted.add(check.capability)
    _CHECKS.append(check.to_dict())


def _install_patches() -> None:
    global _INSTALLED, _ENV_PROXY
    if _INSTALLED:
        return
    _ORIGINALS["open"] = builtins.open
    _ORIGINALS["path_open"] = Path.open
    _ORIGINALS["os_open"] = os.open
    _ORIGINALS["urlopen"] = urllib_request.urlopen
    _ORIGINALS["socket_connect"] = socket.socket.connect
    _ORIGINALS["create_connection"] = socket.create_connection
    _ORIGINALS["popen"] = subprocess.Popen
    _ORIGINALS["run"] = subprocess.run
    _ORIGINALS["call"] = subprocess.call
    _ORIGINALS["system"] = os.system
    _ORIGINALS["getenv"] = os.getenv
    _ORIGINALS["putenv"] = os.putenv
    _ORIGINALS["environ"] = os.environ

    builtins.open = _patched_open  # type: ignore[assignment]
    Path.open = _patched_path_open  # type: ignore[assignment]
    os.open = _patched_os_open  # type: ignore[assignment]
    urllib_request.urlopen = _patched_urlopen  # type: ignore[assignment]
    socket.socket.connect = _patched_socket_connect  # type: ignore[assignment]
    socket.create_connection = _patched_create_connection  # type: ignore[assignment]
    subprocess.Popen = _patched_popen  # type: ignore[assignment]
    subprocess.run = _patched_run  # type: ignore[assignment]
    subprocess.call = _patched_call  # type: ignore[assignment]
    os.system = _patched_system  # type: ignore[assignment]
    os.getenv = _patched_getenv  # type: ignore[assignment]
    os.putenv = _patched_putenv  # type: ignore[assignment]

    _ENV_PROXY = EnvProxy(_ORIGINALS["environ"])  # type: ignore[arg-type]
    os.environ = _ENV_PROXY  # type: ignore[assignment]
    _INSTALLED = True


def _patched_open(path, mode="r", *args, **kwargs):
    if _CONTEXT:
        check_filesystem(_CONTEXT, _record_check, path=path, mode=mode)
    return _ORIGINALS["open"](path, mode, *args, **kwargs)


def _patched_path_open(self, *args, **kwargs):
    mode = "r"
    if args:
        mode = args[0]
    elif "mode" in kwargs:
        mode = kwargs["mode"]
    if _CONTEXT:
        check_filesystem(_CONTEXT, _record_check, path=self, mode=mode)
    return _ORIGINALS["path_open"](self, *args, **kwargs)


def _patched_os_open(path, flags, *args, **kwargs):
    if _CONTEXT:
        mode = _mode_from_flags(flags)
        check_filesystem(_CONTEXT, _record_check, path=path, mode=mode)
    return _ORIGINALS["os_open"](path, flags, *args, **kwargs)


def _patched_urlopen(req, *args, **kwargs):
    url, method = _url_and_method(req)
    if _CONTEXT:
        check_network(_CONTEXT, _record_check, url=url, method=method)
    return _ORIGINALS["urlopen"](req, *args, **kwargs)


def _patched_socket_connect(self, address):
    if _CONTEXT:
        url = _socket_url(address)
        check_network(_CONTEXT, _record_check, url=url, method="CONNECT")
    return _ORIGINALS["socket_connect"](self, address)


def _patched_create_connection(address, *args, **kwargs):
    if _CONTEXT:
        url = _socket_url(address)
        check_network(_CONTEXT, _record_check, url=url, method="CONNECT")
    return _ORIGINALS["create_connection"](address, *args, **kwargs)


def _patched_popen(*popenargs, **kwargs):
    if _CONTEXT:
        argv = _extract_argv(popenargs, kwargs)
        check_subprocess(_CONTEXT, _record_check, argv=argv)
    return _ORIGINALS["popen"](*popenargs, **kwargs)


def _patched_run(*popenargs, **kwargs):
    if _CONTEXT:
        argv = _extract_argv(popenargs, kwargs)
        check_subprocess(_CONTEXT, _record_check, argv=argv)
    return _ORIGINALS["run"](*popenargs, **kwargs)


def _patched_call(*popenargs, **kwargs):
    if _CONTEXT:
        argv = _extract_argv(popenargs, kwargs)
        check_subprocess(_CONTEXT, _record_check, argv=argv)
    return _ORIGINALS["call"](*popenargs, **kwargs)


def _patched_system(command):
    if _CONTEXT:
        check_subprocess(_CONTEXT, _record_check, argv=[str(command)])
    return _ORIGINALS["system"](command)


def _patched_getenv(key, default=None):
    if _CONTEXT:
        _check_env_read(key)
    return _ORIGINALS["getenv"](key, default)


def _patched_putenv(key, value):
    if _CONTEXT:
        _check_env_write(key)
    return _ORIGINALS["putenv"](key, value)


def _check_env_read(key: str) -> None:
    if _CONTEXT is None:
        return
    key_text = str(key)
    check_env_read(_CONTEXT, _record_check, key=key_text)
    secret_name = normalize_secret_name(key_text)
    if secret_name:
        check_secret_allowed(_CONTEXT, _record_check, secret_name=secret_name)


def _check_env_write(key: str) -> None:
    if _CONTEXT is None:
        return
    key_text = str(key)
    check_env_write(_CONTEXT, _record_check, key=key_text)
    secret_name = normalize_secret_name(key_text)
    if secret_name:
        check_secret_allowed(_CONTEXT, _record_check, secret_name=secret_name)


def _url_and_method(req) -> tuple[str, str]:
    if isinstance(req, urllib_request.Request):
        return req.full_url, req.get_method()
    return str(req), "GET"


def _socket_url(address) -> str:
    if isinstance(address, tuple) and len(address) >= 2:
        host, port = address[0], address[1]
        return f"socket://{host}:{port}"
    return f"socket://{address}"


def _extract_argv(popenargs, kwargs) -> list[str]:
    cmd = None
    if "args" in kwargs:
        cmd = kwargs.get("args")
    elif popenargs:
        cmd = popenargs[0]
    if isinstance(cmd, (list, tuple)):
        return [str(item) for item in cmd]
    if cmd is None:
        return []
    return [str(cmd)]


def _mode_from_flags(flags: int) -> str:
    if _is_write_flags(flags):
        return "w"
    return "r"


def _is_write_flags(flags: int) -> bool:
    write_flags = (
        os.O_WRONLY
        | os.O_RDWR
        | os.O_APPEND
        | os.O_CREAT
        | os.O_TRUNC
        | getattr(os, "O_EXCL", 0)
    )
    return bool(flags & write_flags)


class EnvProxy(MutableMapping):
    def __init__(self, raw):
        self._raw = raw

    def __getitem__(self, key):
        if _CONTEXT:
            _check_env_read(key)
        return self._raw[key]

    def __setitem__(self, key, value):
        if _CONTEXT:
            _check_env_write(key)
        self._raw[key] = value

    def __delitem__(self, key):
        if _CONTEXT:
            _check_env_write(key)
        del self._raw[key]

    def __iter__(self):
        if _CONTEXT:
            _check_env_read("*")
        return iter(self._raw)

    def __len__(self) -> int:
        if _CONTEXT:
            _check_env_read("*")
        return len(self._raw)

    def get(self, key, default=None):
        if _CONTEXT:
            _check_env_read(key)
        return self._raw.get(key, default)

    def update(self, other=(), **kwargs):
        if isinstance(other, dict):
            items = list(other.items())
        else:
            items = list(other)
        items.extend(kwargs.items())
        for key, value in items:
            self.__setitem__(key, value)


__all__ = ["run"]
