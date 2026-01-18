from __future__ import annotations

import json
from pathlib import Path
from urllib import request

from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.packs.runtime_paths import pack_job_queue_path
from namel3ss_safeio import filesystem_root as safeio_filesystem_root
from namel3ss_safeio import safe_open, safe_urlopen


def read_text(path: str | Path, *, encoding: str = "utf-8") -> str:
    with safe_open(path, "r", encoding=encoding) as handle:
        return handle.read()


def write_text(
    path: str | Path,
    content: str,
    *,
    encoding: str = "utf-8",
    create_dirs: bool = False,
) -> int:
    if not isinstance(content, str):
        raise ValueError("content must be text")
    with safe_open(path, "w", encoding=encoding, create_dirs=create_dirs) as handle:
        handle.write(content)
    return len(content.encode(encoding))


def read_json(path: str | Path, *, encoding: str = "utf-8") -> object:
    return json.loads(read_text(path, encoding=encoding))


def write_json(
    path: str | Path,
    payload: object,
    *,
    encoding: str = "utf-8",
    create_dirs: bool = False,
) -> int:
    text = canonical_json_dumps(payload, pretty=True)
    return write_text(path, text, encoding=encoding, create_dirs=create_dirs)


def http_get_json(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout_seconds: int = 10,
) -> dict[str, object]:
    if not isinstance(url, str) or not url.strip():
        raise ValueError("url must be a non-empty string")
    header_map = _normalize_headers(headers)
    req = request.Request(url, method="GET", headers=header_map)
    with safe_urlopen(req, timeout=timeout_seconds) as resp:
        status = int(getattr(resp, "status", None) or resp.getcode())
        raw = resp.read()
        body = raw.decode("utf-8", errors="replace")
        response_headers = _sorted_headers(resp.headers.items())
    payload: dict[str, object] = {"status": status, "headers": response_headers, "body": body}
    try:
        payload["json"] = json.loads(body)
    except Exception:
        pass
    return payload


def enqueue_job(job_name: str, payload: object | None = None) -> None:
    if not isinstance(job_name, str) or not job_name.strip():
        raise ValueError("job_name must be a non-empty string")
    root = _runtime_root()
    entry = {"job": job_name.strip(), "payload": payload if payload is not None else {}}
    _append_job_entry(root, entry)


def drain_job_requests(root: Path) -> list[dict[str, object]]:
    path = pack_job_queue_path(root)
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    path.unlink(missing_ok=True)
    requests: list[dict[str, object]] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as err:
            raise Namel3ssError(f"Pack job request is invalid: {err.msg}") from err
        if not isinstance(entry, dict):
            raise Namel3ssError("Pack job request must be an object")
        job = entry.get("job")
        if not isinstance(job, str) or not job.strip():
            raise Namel3ssError("Pack job request must include a job name")
        requests.append({"job": job, "payload": entry.get("payload")})
    return requests


def _runtime_root() -> Path:
    root = safeio_filesystem_root()
    if not root:
        raise Namel3ssError("Pack runtime root is not available")
    return Path(root)


def _append_job_entry(root: Path, entry: dict[str, object]) -> None:
    path = pack_job_queue_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = canonical_json_dumps(entry, pretty=False)
    with safe_open(path, "a", encoding="utf-8", create_dirs=True) as handle:
        handle.write(line)
        handle.write("\n")


def _normalize_headers(headers: dict[str, str] | None) -> dict[str, str]:
    if not headers:
        return {}
    normalized: dict[str, str] = {}
    for key, value in headers.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise ValueError("headers must be a string map")
        normalized[key.strip()] = value.strip()
    return normalized


def _sorted_headers(pairs) -> list[dict[str, str]]:
    headers: list[dict[str, str]] = []
    for key, value in pairs:
        headers.append({"name": str(key).strip(), "value": str(value).strip()})
    return sorted(headers, key=lambda item: item["name"])


__all__ = [
    "drain_job_requests",
    "enqueue_job",
    "http_get_json",
    "read_json",
    "read_text",
    "write_json",
    "write_text",
]
