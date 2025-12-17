from __future__ import annotations

from urllib.error import HTTPError, URLError

from namel3ss.errors.base import Namel3ssError


def require_env(provider_name: str, env_var: str, value: str | None) -> str:
    if value is None or str(value).strip() == "":
        short_var = env_var.replace("NAMEL3SS_", "")
        raise Namel3ssError(f"Missing {short_var} (set it in .env or export it)")
    return value


def map_http_error(provider_name: str, err: HTTPError | URLError | TimeoutError | Exception) -> Namel3ssError:
    if isinstance(err, HTTPError) and err.code in {401, 403}:
        return Namel3ssError(f"Provider '{provider_name}' authentication failed")
    if isinstance(err, (URLError, TimeoutError)):
        return Namel3ssError(f"Provider '{provider_name}' unreachable")
    return Namel3ssError(f"Provider '{provider_name}' returned an invalid response")
