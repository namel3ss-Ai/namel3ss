from __future__ import annotations

import functools
import os
import ssl
import subprocess
import sys

_DISABLE_TLS_FALLBACK_ENV = "N3_DISABLE_MACOS_TLS_FALLBACK"
_DISABLE_TLS_FALLBACK_VALUES = {"1", "true", "yes"}


def safe_urlopen_with_tls_fallback(req, *, timeout_seconds: int):
    from namel3ss_safeio import safe_urlopen

    return open_url_with_tls_fallback(safe_urlopen, req, timeout_seconds=timeout_seconds)


def open_url_with_tls_fallback(open_func, req, *, timeout_seconds: int):
    try:
        return open_func(req, timeout=timeout_seconds)
    except Exception as err:
        if not _should_retry_with_macos_trust(err):
            raise
        context = _macos_ssl_context()
        if context is None:
            raise
        try:
            return open_func(req, timeout=timeout_seconds, context=context)
        except TypeError:
            # Some test doubles patch URL opener callables without kwargs support.
            raise err


def _should_retry_with_macos_trust(err: Exception) -> bool:
    if sys.platform != "darwin":
        return False
    if _tls_fallback_disabled():
        return False
    return _contains_cert_verify_failure(err)


def _contains_cert_verify_failure(err: Exception) -> bool:
    pending: list[BaseException] = [err]
    seen: set[int] = set()
    while pending:
        current = pending.pop()
        marker = id(current)
        if marker in seen:
            continue
        seen.add(marker)
        if isinstance(current, ssl.SSLCertVerificationError):
            return True
        message = str(current).lower()
        if "certificate verify failed" in message:
            return True
        if "unable to get local issuer certificate" in message:
            return True
        reason = getattr(current, "reason", None)
        if isinstance(reason, BaseException):
            pending.append(reason)
        cause = getattr(current, "__cause__", None)
        if isinstance(cause, BaseException):
            pending.append(cause)
        context = getattr(current, "__context__", None)
        if isinstance(context, BaseException):
            pending.append(context)
    return False


@functools.lru_cache(maxsize=1)
def _macos_ssl_context() -> ssl.SSLContext | None:
    if sys.platform != "darwin":
        return None
    if _tls_fallback_disabled():
        return None
    root_bundle = _read_macos_system_root_bundle()
    if root_bundle is None:
        return None
    context = ssl.create_default_context()
    try:
        context.load_verify_locations(cadata=root_bundle)
    except Exception:
        return None
    return context


@functools.lru_cache(maxsize=1)
def _read_macos_system_root_bundle() -> str | None:
    if sys.platform != "darwin":
        return None
    try:
        result = subprocess.run(
            [
                "security",
                "find-certificate",
                "-a",
                "-p",
                "/System/Library/Keychains/SystemRootCertificates.keychain",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=8,
        )
    except Exception:
        return None
    if result.returncode != 0:
        return None
    bundle = result.stdout
    if "BEGIN CERTIFICATE" not in bundle:
        return None
    return bundle


def _tls_fallback_disabled() -> bool:
    value = os.getenv(_DISABLE_TLS_FALLBACK_ENV, "")
    return value.strip().lower() in _DISABLE_TLS_FALLBACK_VALUES


__all__ = ["open_url_with_tls_fallback", "safe_urlopen_with_tls_fallback"]
