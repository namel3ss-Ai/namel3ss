from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import ast
import sys

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message


VENV_DIRNAME = ".venv"
LOCKFILE_NAME = "requirements.lock.txt"
REQUIREMENTS_FILE = "requirements.txt"
PYPROJECT_FILE = "pyproject.toml"


@dataclass(frozen=True)
class DependencyInfo:
    kind: str
    path: Path | None
    warning: str | None = None


@dataclass(frozen=True)
class PythonEnvInfo:
    env_kind: str
    python_path: Path
    venv_path: Path | None


@dataclass(frozen=True)
class DepsStatus:
    app_root: Path
    venv_path: Path
    venv_exists: bool
    python_path: Path
    dependency_info: DependencyInfo
    lockfile_path: Path | None
    last_install_time: str | None


def app_venv_path(app_root: Path) -> Path:
    return app_root / VENV_DIRNAME


def venv_python_path(venv_path: Path) -> Path:
    if sys.platform.startswith("win"):
        return venv_path / "Scripts" / "python.exe"
    return venv_path / "bin" / "python"


def lockfile_path(app_root: Path) -> Path:
    return app_root / LOCKFILE_NAME


def detect_dependency_info(app_root: Path) -> DependencyInfo:
    pyproject_path = app_root / PYPROJECT_FILE
    requirements_path = app_root / REQUIREMENTS_FILE
    if pyproject_path.exists() and requirements_path.exists():
        warning = "Both pyproject.toml and requirements.txt found; using pyproject.toml."
        return DependencyInfo(kind="pyproject", path=pyproject_path, warning=warning)
    if pyproject_path.exists():
        return DependencyInfo(kind="pyproject", path=pyproject_path, warning=None)
    if requirements_path.exists():
        return DependencyInfo(kind="requirements", path=requirements_path, warning=None)
    return DependencyInfo(kind="none", path=None, warning=None)


def load_pyproject_dependencies(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    tomllib = _load_tomllib()
    if tomllib is not None:
        try:
            data = tomllib.loads(text)
        except Exception as err:
            raise Namel3ssError(
                build_guidance_message(
                    what="pyproject.toml could not be parsed.",
                    why=str(err),
                    fix="Fix the TOML syntax in pyproject.toml.",
                    example='[project]\nname = "demo"\ndependencies = ["requests==2.31.0"]',
                )
            ) from err
        project = data.get("project") if isinstance(data, dict) else None
        if not isinstance(project, dict):
            return []
        deps = project.get("dependencies", [])
        if deps is None:
            return []
        if not isinstance(deps, list) or any(not isinstance(item, str) for item in deps):
            raise Namel3ssError(
                build_guidance_message(
                    what="pyproject.toml dependencies are invalid.",
                    why="[project].dependencies must be a list of strings.",
                    fix="Update pyproject.toml to use a list of dependency strings.",
                    example='[project]\ndependencies = ["requests==2.31.0"]',
                )
            )
        return deps
    return _parse_pyproject_dependencies_minimal(text, path)


def resolve_python_env(app_root: Path, *, system_python: str | None = None) -> PythonEnvInfo:
    venv_path = app_venv_path(app_root)
    python_path = venv_python_path(venv_path)
    if venv_path.exists():
        if not python_path.exists():
            raise Namel3ssError(
                build_guidance_message(
                    what="Venv exists but python was not found.",
                    why=f"Expected python at {python_path}.",
                    fix="Recreate the venv with `n3 deps install --force`.",
                    example="n3 deps install --force",
                )
            )
        return PythonEnvInfo(env_kind="venv", python_path=python_path, venv_path=venv_path)
    system_value = system_python or sys.executable
    return PythonEnvInfo(env_kind="system", python_path=Path(system_value), venv_path=None)


def build_deps_status(app_root: Path) -> DepsStatus:
    venv_path = app_venv_path(app_root)
    venv_exists = venv_path.exists()
    env_info = resolve_python_env(app_root)
    dep_info = detect_dependency_info(app_root)
    lock_path = lockfile_path(app_root)
    lockfile = lock_path if lock_path.exists() else None
    last_time = _last_install_time(lockfile, venv_path if venv_exists else None)
    return DepsStatus(
        app_root=app_root,
        venv_path=venv_path,
        venv_exists=venv_exists,
        python_path=env_info.python_path,
        dependency_info=dep_info,
        lockfile_path=lockfile,
        last_install_time=last_time,
    )


def _last_install_time(lockfile: Path | None, venv_path: Path | None) -> str | None:
    candidate = None
    if lockfile and lockfile.exists():
        candidate = lockfile
    elif venv_path and venv_path.exists():
        cfg = venv_path / "pyvenv.cfg"
        candidate = cfg if cfg.exists() else venv_path
    if not candidate:
        return None
    ts = candidate.stat().st_mtime
    return datetime.fromtimestamp(ts).isoformat(timespec="seconds")


def _load_tomllib():
    try:
        import tomllib  # type: ignore
    except Exception:
        try:
            import tomli as tomllib  # type: ignore
        except Exception:
            return None
    return tomllib


def _parse_pyproject_dependencies_minimal(text: str, path: Path) -> list[str]:
    in_project = False
    collecting = False
    buffer = ""
    line_num = 0
    for raw_line in text.splitlines():
        line_num += 1
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].strip()
            in_project = section == "project"
            collecting = False
            continue
        if not in_project:
            continue
        if collecting:
            buffer = f"{buffer} {_strip_inline_comment(line)}"
            if "]" in line:
                return _parse_dependency_list(buffer, path, line_num)
            continue
        if not line.startswith("dependencies"):
            continue
        if "=" not in line:
            raise _pyproject_dependencies_error(path, line_num)
        _, value = line.split("=", 1)
        value = _strip_inline_comment(value.strip())
        if not value:
            return []
        if value.startswith("[") and "]" in value:
            return _parse_dependency_list(value, path, line_num)
        if value.startswith("["):
            collecting = True
            buffer = value
            if "]" in value:
                return _parse_dependency_list(value, path, line_num)
            continue
        raise _pyproject_dependencies_error(path, line_num)
    return []


def _parse_dependency_list(value: str, path: Path, line_num: int) -> list[str]:
    cleaned = _strip_inline_comment(value).strip()
    try:
        parsed = ast.literal_eval(cleaned)
    except Exception as err:
        raise _pyproject_dependencies_error(path, line_num, err) from err
    if not isinstance(parsed, list) or any(not isinstance(item, str) for item in parsed):
        raise _pyproject_dependencies_error(path, line_num)
    return parsed


def _strip_inline_comment(line: str) -> str:
    result = []
    in_string = False
    escape = False
    for ch in line:
        if escape:
            result.append(ch)
            escape = False
            continue
        if ch == "\\" and in_string:
            escape = True
            result.append(ch)
            continue
        if ch == '"':
            in_string = not in_string
            result.append(ch)
            continue
        if ch == "#" and not in_string:
            break
        result.append(ch)
    return "".join(result).strip()


def _pyproject_dependencies_error(path: Path, line_num: int, err: Exception | None = None) -> Namel3ssError:
    detail = f" ({err})" if err else ""
    return Namel3ssError(
        build_guidance_message(
            what="pyproject.toml dependencies are invalid.",
            why=f"[project].dependencies must be a list of strings{detail}.",
            fix="Use a list of dependency strings or switch to requirements.txt.",
            example='[project]\ndependencies = ["requests==2.31.0"]',
        ),
        line=line_num,
        column=1,
    )


__all__ = [
    "DepsStatus",
    "DependencyInfo",
    "PythonEnvInfo",
    "VENV_DIRNAME",
    "LOCKFILE_NAME",
    "REQUIREMENTS_FILE",
    "PYPROJECT_FILE",
    "app_venv_path",
    "build_deps_status",
    "detect_dependency_info",
    "load_pyproject_dependencies",
    "lockfile_path",
    "resolve_python_env",
    "venv_python_path",
]
