from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "examples" / "embed" / "c" / "main.c"
FIXTURE = ROOT / "tests" / "fixtures" / "embed" / "c_hash.txt"


def _find_tool(names: tuple[str, ...]) -> str | None:
    for name in names:
        path = shutil.which(name)
        if path is not None:
            return path
    return None


def _library_name() -> str:
    if sys.platform.startswith("win"):
        return "namel3ss_native.dll"
    if sys.platform == "darwin":
        return "libnamel3ss_native.dylib"
    return "libnamel3ss_native.so"


def _find_library(target_dir: Path) -> Path | None:
    name = _library_name()
    for candidate in target_dir.rglob(name):
        if candidate.is_file():
            return candidate
    return None


@pytest.mark.skipif(sys.platform.startswith("win"), reason="native embed example is not supported on windows")
def test_embed_c_example(tmp_path: Path) -> None:
    cc = _find_tool(("cc", "clang", "gcc"))
    cargo = shutil.which("cargo")
    if cc is None or cargo is None:
        pytest.skip("native toolchain not available")

    native_src = ROOT / "native"
    native_copy = tmp_path / "native"
    shutil.copytree(native_src, native_copy)

    target_dir = tmp_path / "target"
    env = os.environ.copy()
    env["CARGO_TARGET_DIR"] = str(target_dir)
    env["CARGO_NET_OFFLINE"] = "true"
    result = subprocess.run(
        [cargo, "build", "--release", "--manifest-path", str(native_copy / "Cargo.toml")],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(result.stderr.strip() or result.stdout.strip())

    lib_path = _find_library(target_dir)
    assert lib_path is not None

    exe_path = tmp_path / "embed_c"
    compile_result = subprocess.run(
        [cc, str(EXAMPLE), "-I", str(native_copy / "include"), str(lib_path), "-o", str(exe_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if compile_result.returncode != 0:
        raise AssertionError(compile_result.stderr.strip() or compile_result.stdout.strip())

    run_env = os.environ.copy()
    lib_dir = str(lib_path.parent)
    if sys.platform == "darwin":
        existing = run_env.get("DYLD_LIBRARY_PATH", "")
        run_env["DYLD_LIBRARY_PATH"] = f"{lib_dir}{os.pathsep}{existing}" if existing else lib_dir
    else:
        existing = run_env.get("LD_LIBRARY_PATH", "")
        run_env["LD_LIBRARY_PATH"] = f"{lib_dir}{os.pathsep}{existing}" if existing else lib_dir

    run_result = subprocess.run(
        [str(exe_path)],
        env=run_env,
        capture_output=True,
        text=True,
        check=False,
    )
    if run_result.returncode != 0:
        raise AssertionError(run_result.stderr.strip() or run_result.stdout.strip())

    expected = FIXTURE.read_text(encoding="utf-8")
    assert run_result.stdout == expected
