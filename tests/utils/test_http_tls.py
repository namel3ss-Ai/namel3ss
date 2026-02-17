from __future__ import annotations

import ssl
from urllib.error import URLError

import pytest

from namel3ss.utils.http_tls import _contains_cert_verify_failure, open_url_with_tls_fallback, safe_urlopen_with_tls_fallback


class _FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def getcode(self):
        return 200


def test_safe_urlopen_with_tls_fallback_retries_with_context(monkeypatch) -> None:
    calls: list[dict] = []

    def fake_urlopen(_req, timeout, **kwargs):
        calls.append(dict(kwargs))
        if "context" not in kwargs:
            raise URLError(
                "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: "
                "unable to get local issuer certificate"
            )
        return _FakeResponse()

    monkeypatch.setattr("namel3ss_safeio.safe_urlopen", fake_urlopen)
    monkeypatch.setattr("namel3ss.utils.http_tls._should_retry_with_macos_trust", lambda _err: True)
    monkeypatch.setattr("namel3ss.utils.http_tls._macos_ssl_context", lambda: ssl.create_default_context())

    with safe_urlopen_with_tls_fallback(object(), timeout_seconds=5) as response:
        assert response.getcode() == 200
    assert len(calls) == 2
    assert "context" in calls[1]


def test_open_url_with_tls_fallback_retries_with_context(monkeypatch) -> None:
    calls: list[dict] = []

    def fake_urlopen(_req, timeout, **kwargs):
        calls.append(dict(kwargs))
        if "context" not in kwargs:
            raise URLError(
                "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: "
                "unable to get local issuer certificate"
            )
        return _FakeResponse()

    monkeypatch.setattr("namel3ss.utils.http_tls._should_retry_with_macos_trust", lambda _err: True)
    monkeypatch.setattr("namel3ss.utils.http_tls._macos_ssl_context", lambda: ssl.create_default_context())

    with open_url_with_tls_fallback(fake_urlopen, object(), timeout_seconds=5) as response:
        assert response.getcode() == 200
    assert len(calls) == 2
    assert "context" in calls[1]


def test_safe_urlopen_with_tls_fallback_reraises_non_cert_error(monkeypatch) -> None:
    def fake_urlopen(_req, timeout, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("namel3ss_safeio.safe_urlopen", fake_urlopen)
    with pytest.raises(RuntimeError, match="boom"):
        safe_urlopen_with_tls_fallback(object(), timeout_seconds=5)


def test_contains_cert_verify_failure_detects_nested_reason() -> None:
    err = URLError(RuntimeError("certificate verify failed: unable to get local issuer certificate"))
    assert _contains_cert_verify_failure(err) is True
