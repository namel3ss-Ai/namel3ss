from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "native" / "Cargo.toml"


def main() -> int:
    if not MANIFEST.exists():
        print("native Cargo.toml not found")
        return 1
    cargo = shutil.which("cargo")
    if cargo is None:
        print("cargo not found")
        return 1
    with tempfile.TemporaryDirectory(prefix="namel3ss-native-build-") as tmp_dir:
        env = os.environ.copy()
        env["CARGO_TARGET_DIR"] = tmp_dir
        result = subprocess.run(
            [cargo, "build", "--manifest-path", str(MANIFEST)],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            sys.stdout.write(result.stdout)
            sys.stderr.write(result.stderr)
            return result.returncode
        lib_path = _find_library(Path(tmp_dir))
        if lib_path is None:
            print("native library not found after build")
            return 1
        if _verify_load(lib_path) != 0:
            return 1
        if _verify_missing_fallback() != 0:
            return 1
    print("native verify ok")
    return 0


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


def _verify_load(lib_path: Path) -> int:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["N3_NATIVE"] = "1"
    env["N3_NATIVE_LIB"] = str(lib_path)
    script = """
from namel3ss.runtime.native import NativeStatus, native_available, native_enabled, native_hash
assert native_enabled() is True
assert native_available() is True
outcome = native_hash(b"native")
assert outcome.status == NativeStatus.OK
assert outcome.payload is not None
"""
    return _run_python(script, env)


def _verify_missing_fallback() -> int:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["N3_NATIVE"] = "1"
    env["N3_NATIVE_LIB"] = "/missing/native/library"
    script = """
from namel3ss.runtime.native import NativeStatus, native_available, native_enabled, native_hash
assert native_enabled() is True
assert native_available() is False
outcome = native_hash(b"native")
assert outcome.status == NativeStatus.NOT_IMPLEMENTED
assert outcome.payload is None
"""
    return _run_python(script, env)


def _run_python(script: str, env: dict) -> int:
    env = dict(env)
    pythonpath = env.get("PYTHONPATH", "")
    src_path = str(ROOT / "src")
    if pythonpath:
        env["PYTHONPATH"] = f"{src_path}{os.pathsep}{pythonpath}"
    else:
        env["PYTHONPATH"] = src_path
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        sys.stdout.write(result.stdout)
        sys.stderr.write(result.stderr)
        return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
