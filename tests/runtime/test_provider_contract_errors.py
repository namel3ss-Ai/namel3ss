import ssl
from urllib.error import HTTPError, URLError

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.ai.providers._shared.errors import map_http_error, require_env


def test_require_env_missing():
    with pytest.raises(Namel3ssError) as err:
        require_env("ollama", "ENV_VAR", None)
    assert "Missing ENV_VAR" in str(err.value)


def test_require_env_present():
    assert require_env("ollama", "ENV_VAR", "value") == "value"


def test_map_http_error_auth():
    err = map_http_error("ollama", HTTPError(url="http://test", code=401, msg="", hdrs=None, fp=None))
    assert str(err) == "Provider 'ollama' authentication failed"
    err = map_http_error("ollama", HTTPError(url="http://test", code=403, msg="", hdrs=None, fp=None))
    assert str(err) == "Provider 'ollama' authentication failed"


def test_map_http_error_unreachable():
    err = map_http_error("ollama", URLError("bad"))
    assert str(err) == "Provider 'ollama' unreachable"
    err = map_http_error("ollama", TimeoutError("timeout"))
    assert str(err) == "Provider 'ollama' unreachable"


def test_map_http_error_invalid():
    err = map_http_error("ollama", Exception("boom"))
    assert str(err) == "Provider 'ollama' returned an invalid response"


def test_map_http_error_network_details_redacted():
    err = map_http_error(
        "ollama",
        URLError(ssl.SSLError("CERTIFICATE_VERIFY_FAILED sk-test Bearer token")),
    )
    diagnostic = err.details.get("diagnostic", {}) if isinstance(err.details, dict) else {}
    network_error = diagnostic.get("network_error") if isinstance(diagnostic, dict) else None
    assert network_error
    assert network_error.get("name") == "SSLError"
    assert "CERTIFICATE_VERIFY_FAILED" in str(network_error.get("message", ""))
    assert "sk-" not in str(network_error.get("message", ""))
    assert "Bearer" not in str(network_error.get("message", ""))
    assert "unreachable" in str(diagnostic.get("message", ""))
