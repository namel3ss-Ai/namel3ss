from __future__ import annotations

import json
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.ai.providers._shared.errors import map_http_error
from namel3ss.runtime.ai.providers._shared.parse import json_loads_or_error
from namel3ss.security import guard_network


def post_json(
    *,
    url: str,
    headers: dict[str, str],
    payload: dict,
    timeout_seconds: int,
    provider_name: str,
    secret_values: Iterable[str] | None = None,
) -> dict:
    data = json.dumps(payload).encode("utf-8")
    request = Request(url, data=data, headers=headers)
    guard_network(url, "POST")
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            body = response.read()
    except HTTPError as err:
        try:
            body = err.read()
        except Exception:
            body = None
        raise map_http_error(provider_name, err, url=url, body=body, secret_values=secret_values) from err
    except (URLError, TimeoutError) as err:
        raise map_http_error(provider_name, err, url=url, secret_values=secret_values) from err
    except Exception as err:  # pragma: no cover - unexpected transport errors
        if isinstance(err, Namel3ssError):
            raise
        raise map_http_error(provider_name, err, url=url, secret_values=secret_values) from err
    return json_loads_or_error(provider_name, body)
