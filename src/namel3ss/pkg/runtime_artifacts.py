from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

from namel3ss.runtime.tools.python_env import app_venv_path, venv_python_path


_PYTHON_CHECKSUM_SCRIPT = """
import hashlib
import importlib.metadata
import json

def _normalize(name):
    return str(name or "").strip().lower().replace("_", "-")

def _checksum_for_distribution(dist):
    files = list(dist.files or [])
    for item in files:
        token = str(item)
        if token.endswith("RECORD"):
            try:
                path = dist.locate_file(item)
                return hashlib.sha256(path.read_bytes()).hexdigest()
            except Exception:
                break
    hasher = hashlib.sha256()
    for item in sorted(str(row) for row in files):
        hasher.update(item.encode("utf-8"))
    hasher.update(str(dist.version or "").encode("utf-8"))
    return hasher.hexdigest()

output = {}
for dist in importlib.metadata.distributions():
    name = dist.metadata.get("Name") or ""
    key = _normalize(name)
    if not key:
        continue
    output[key] = _checksum_for_distribution(dist)
print(json.dumps(output, sort_keys=True))
""".strip()


def collect_python_artifact_checksums(root: Path) -> dict[str, str]:
    venv_path = app_venv_path(root)
    if not venv_path.exists():
        return {}
    python_path = venv_python_path(venv_path)
    if not python_path.exists():
        return {}
    result = subprocess.run(
        [str(python_path), "-c", _PYTHON_CHECKSUM_SCRIPT],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return {}
    try:
        payload = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, dict):
        return {}
    output: dict[str, str] = {}
    for key, value in payload.items():
        name = _normalize_name(str(key))
        checksum = str(value or "").strip().lower()
        if name and checksum:
            output[name] = checksum
    return output


def collect_system_artifact_checksums(specs: tuple[str, ...]) -> dict[str, str]:
    output: dict[str, str] = {}
    for spec in sorted(set(specs)):
        name = _system_name(spec)
        if not name:
            continue
        checksum = _system_checksum(name)
        if checksum:
            output[_normalize_name(name)] = checksum
    return output


def _system_name(spec: str) -> str:
    text = str(spec or "").strip()
    if not text:
        return ""
    if "@" in text:
        return text.rsplit("@", 1)[0].strip()
    return text


def _system_checksum(name: str) -> str | None:
    dpkg = shutil.which("dpkg-query")
    if dpkg:
        result = subprocess.run(
            [dpkg, "-W", "-f=${Version}", name],
            capture_output=True,
            text=True,
            check=False,
        )
        version = str(result.stdout or "").strip()
        if result.returncode == 0 and version:
            token = f"dpkg|{name}|{version}"
            return hashlib.sha256(token.encode("utf-8")).hexdigest()
    brew = shutil.which("brew")
    if brew:
        result = subprocess.run(
            [brew, "list", "--versions", name],
            capture_output=True,
            text=True,
            check=False,
        )
        line = str(result.stdout or "").strip()
        if result.returncode == 0 and line:
            parts = line.split()
            version = parts[1] if len(parts) > 1 else "*"
            token = f"brew|{name}|{version}"
            return hashlib.sha256(token.encode("utf-8")).hexdigest()
    return None


def _normalize_name(value: str) -> str:
    return str(value or "").strip().lower().replace("_", "-")


__all__ = [
    "collect_python_artifact_checksums",
    "collect_system_artifact_checksums",
]
