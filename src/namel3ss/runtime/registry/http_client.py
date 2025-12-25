from __future__ import annotations

import json
from pathlib import Path
from urllib.request import Request, urlopen

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message


def fetch_registry_entries(
    base_url: str,
    *,
    phrase: str,
    capability: str | None,
    risk: str | None,
) -> list[dict[str, object]]:
    url = _join(base_url, "search")
    payload = {"phrase": phrase, "capability": capability, "risk": risk}
    request = Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
    try:
        with urlopen(request, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as err:
        raise Namel3ssError(_registry_fetch_message(base_url, str(err))) from err
    if isinstance(data, dict):
        entries = data.get("entries")
        if isinstance(entries, list):
            return [item for item in entries if isinstance(item, dict)]
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    return []


def fetch_registry_bundle(base_url: str, digest: str, *, cache_path: Path) -> Path:
    url = _join(base_url, f"bundle/{digest}")
    try:
        with urlopen(url, timeout=10) as resp:
            payload = resp.read()
    except Exception as err:
        raise Namel3ssError(_registry_fetch_message(base_url, str(err))) from err
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_bytes(payload)
    return cache_path


def _join(base_url: str, suffix: str) -> str:
    return f"{base_url.rstrip('/')}/{suffix}"


def _registry_fetch_message(base_url: str, details: str) -> str:
    return build_guidance_message(
        what="Registry fetch failed.",
        why=f"Unable to reach {base_url}: {details}.",
        fix="Check the registry URL or try again.",
        example="n3 discover \"send email\"",
    )


__all__ = ["fetch_registry_bundle", "fetch_registry_entries"]
