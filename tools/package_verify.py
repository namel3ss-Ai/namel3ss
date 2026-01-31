from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import venv


ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_SUBSTRINGS = ("/Users/", "/home/", "C:\\")
TRUTHY = {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class PackagePlan:
    temp_root: Path
    stage_dir: Path
    dist_dir: Path
    venv_dir: Path


def plan_paths() -> PackagePlan:
    temp_root = Path(tempfile.mkdtemp(prefix="namel3ss-package-"))
    stage_dir = temp_root / "stage"
    dist_dir = temp_root / "dist"
    venv_dir = temp_root / "venv"
    return PackagePlan(temp_root=temp_root, stage_dir=stage_dir, dist_dir=dist_dir, venv_dir=venv_dir)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify deterministic packaging behavior.")
    parser.add_argument("--build-only", action="store_true", help="Build wheel(s) only.")
    args = parser.parse_args(argv)

    plan = plan_paths()
    try:
        if not _ensure_build_deps():
            print("Package verify skipped: build dependencies missing.")
            return 0
        stage_repo(ROOT, plan.stage_dir)
        if _truthy_env("N3_BUILD_NATIVE"):
            _build_native(plan.stage_dir)
        wheel_path = build_wheel(plan.stage_dir, plan.dist_dir)
        if args.build_only:
            print(f"Wheel build ok: {wheel_path.name}")
            return 0
        verify_wheel(plan, wheel_path)
    except RuntimeError as exc:
        print(f"Package verify failed: {exc}", file=sys.stderr)
        return 1
    finally:
        shutil.rmtree(plan.temp_root, ignore_errors=True)
    print("Package verify ok.")
    return 0


def stage_repo(repo_root: Path, stage_dir: Path) -> None:
    ignore_names = {
        ".git",
        ".hg",
        ".svn",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "__pycache__",
        "build",
        "dist",
        ".venv",
        ".tox",
        ".idea",
        ".vscode",
        "tmp_tool_test",
    }

    def _ignore(path: str, names: list[str]) -> set[str]:
        ignored: set[str] = set()
        for name in names:
            if name in ignore_names or name.endswith(".pyc"):
                ignored.add(name)
        if Path(path).name == "native" and "target" in names:
            ignored.add("target")
        return ignored

    shutil.copytree(repo_root, stage_dir, ignore=_ignore)


def _build_native(stage_dir: Path) -> None:
    manifest = stage_dir / "native" / "Cargo.toml"
    if not manifest.exists():
        return
    cargo = shutil.which("cargo")
    if cargo is None:
        return
    target_dir = stage_dir / "native" / "target"
    env = os.environ.copy()
    env["CARGO_TARGET_DIR"] = str(target_dir)
    run([cargo, "build", "--release", "--manifest-path", str(manifest)], env=env, cwd=stage_dir)
    lib_path = _find_library(target_dir)
    if lib_path is None:
        return
    dest_dir = stage_dir / "src" / "namel3ss" / "runtime" / "native" / "lib"
    dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(lib_path, dest_dir / lib_path.name)


def _find_library(target_dir: Path) -> Path | None:
    name = _library_name()
    for candidate in target_dir.rglob(name):
        if candidate.is_file():
            return candidate
    return None


def _library_name() -> str:
    if sys.platform.startswith("win"):
        return "namel3ss_native.dll"
    if sys.platform == "darwin":
        return "libnamel3ss_native.dylib"
    return "libnamel3ss_native.so"


def build_wheel(stage_dir: Path, dist_dir: Path) -> Path:
    dist_dir.mkdir(parents=True, exist_ok=True)
    env = _base_env()
    env.update(
        {
            "PIP_DISABLE_PIP_VERSION_CHECK": "1",
            "PIP_NO_INPUT": "1",
            "PIP_NO_CACHE_DIR": "1",
            "PIP_NO_INDEX": "1",
        }
    )
    run(
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            ".",
            "--no-deps",
            "--no-build-isolation",
            "--wheel-dir",
            str(dist_dir),
        ],
        env=env,
        cwd=stage_dir,
    )
    wheel_path = _find_wheel(dist_dir)
    if wheel_path is None:
        raise RuntimeError("Wheel build produced no artifacts.")
    return wheel_path


def verify_wheel(plan: PackagePlan, wheel_path: Path) -> None:
    venv.EnvBuilder(with_pip=True, clear=True).create(plan.venv_dir)
    python_bin = _venv_python(plan.venv_dir)
    env = _base_env()
    env.update(
        {
            "PIP_DISABLE_PIP_VERSION_CHECK": "1",
            "PIP_NO_INPUT": "1",
            "PIP_NO_CACHE_DIR": "1",
            "PIP_NO_INDEX": "1",
            "PIP_FIND_LINKS": str(plan.dist_dir),
        }
    )
    run([str(python_bin), "-m", "pip", "install", str(wheel_path)], env=env)
    n3_bin = _venv_script(plan.venv_dir, "n3")
    run([str(n3_bin), "--help"], env=env, cwd=ROOT)
    run([str(n3_bin), "--version"], env=env, cwd=ROOT)
    _verify_doc(n3_bin, env)
    _verify_audit(n3_bin, env)
    _verify_native_fallback(n3_bin, env)


def _verify_doc(n3_bin: Path, env: dict[str, str]) -> None:
    output = _run_capture([str(n3_bin), "doc"], env=env, cwd=ROOT)
    _assert_no_forbidden(output)
    expected = (ROOT / "tests" / "fixtures" / "doctor" / "doc_golden.json").read_text(encoding="utf-8")
    if output != expected:
        raise RuntimeError("doc output drifted from golden.")
    second = _run_capture([str(n3_bin), "doc"], env=env, cwd=ROOT)
    if output != second:
        raise RuntimeError("doc output is not deterministic.")


def _verify_audit(n3_bin: Path, env: dict[str, str]) -> None:
    fixture_root = ROOT / "tests" / "fixtures" / "doctor"
    output = _run_capture(
        [
            str(n3_bin),
            "explain",
            "--audit",
            "--json",
            "--input",
            str((fixture_root / "audit_input.json").relative_to(ROOT)),
            str((fixture_root / "app.ai").relative_to(ROOT)),
        ],
        env=env,
        cwd=ROOT,
    )
    expected = (fixture_root / "audit_golden.json").read_text(encoding="utf-8")
    if output != expected:
        raise RuntimeError("explain --audit output drifted from golden.")


def _verify_native_fallback(n3_bin: Path, env: dict[str, str]) -> None:
    disabled = dict(env)
    disabled.pop("N3_NATIVE", None)
    disabled.pop("N3_NATIVE_LIB", None)
    payload = json.loads(_run_capture([str(n3_bin), "doc"], env=disabled, cwd=ROOT))
    native = payload.get("native") if isinstance(payload, dict) else {}
    if native.get("enabled") is not False:
        raise RuntimeError("native disabled mode not reported correctly.")

    enabled = dict(env)
    enabled["N3_NATIVE"] = "1"
    enabled["N3_NATIVE_LIB"] = "/missing/native/library"
    payload = json.loads(_run_capture([str(n3_bin), "doc"], env=enabled, cwd=ROOT))
    native = payload.get("native") if isinstance(payload, dict) else {}
    if native.get("enabled") is not True or native.get("available") is not False:
        raise RuntimeError("native missing fallback not reported correctly.")


def _base_env() -> dict[str, str]:
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.pop("N3_NATIVE", None)
    env.pop("N3_NATIVE_LIB", None)
    env.pop("N3_PERSIST_ROOT", None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def _venv_python(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def _venv_script(venv_dir: Path, name: str) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / f"{name}.exe"
    return venv_dir / "bin" / name


def run(cmd: list[str], *, env: dict[str, str] | None = None, cwd: Path | None = None) -> None:
    result = subprocess.run(cmd, cwd=cwd, env=env, text=True, capture_output=True)
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip()
        suffix = f"\n{message}" if message else ""
        raise RuntimeError(f"Command failed: {' '.join(cmd)}{suffix}")


def _run_capture(cmd: list[str], *, env: dict[str, str] | None = None, cwd: Path | None = None) -> str:
    result = subprocess.run(cmd, cwd=cwd, env=env, text=True, capture_output=True)
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip()
        suffix = f"\n{message}" if message else ""
        raise RuntimeError(f"Command failed: {' '.join(cmd)}{suffix}")
    return result.stdout


def _find_wheel(dist_dir: Path) -> Path | None:
    candidates = sorted(dist_dir.glob("*.whl"))
    return candidates[0] if candidates else None


def _ensure_build_deps() -> None:
    try:
        import setuptools  # noqa: F401
        import wheel  # noqa: F401
    except Exception:
        return False
    return True


def _assert_no_forbidden(text: str) -> None:
    for item in FORBIDDEN_SUBSTRINGS:
        if item in text:
            raise RuntimeError("output contains forbidden host path markers.")


def _truthy_env(name: str) -> bool:
    value = os.getenv(name, "")
    return value.strip().lower() in TRUTHY


__all__ = ["FORBIDDEN_SUBSTRINGS", "PackagePlan", "plan_paths"]


if __name__ == "__main__":
    raise SystemExit(main())
