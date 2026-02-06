from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message


def run_wasm_module(module_path: Path, *, input_json: str) -> dict[str, object]:
    path = Path(module_path)
    if not path.exists() or not path.is_file():
        raise Namel3ssError(_missing_module_message(path))

    runtime = _resolve_runtime()
    if runtime is None:
        raise Namel3ssError(_missing_runtime_message())

    command = _build_command(runtime, path, input_json)
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )
    stdout = (result.stdout or "").strip()
    stderr = (result.stderr or "").strip()

    if result.returncode != 0:
        detail = stderr or stdout or f"runtime exited with status {result.returncode}"
        raise Namel3ssError(_runtime_failed_message(runtime, detail))

    parsed_output: object
    if not stdout:
        parsed_output = None
    else:
        try:
            parsed_output = json.loads(stdout)
        except Exception:
            parsed_output = stdout

    return {
        "ok": True,
        "runtime": runtime,
        "module": path.as_posix(),
        "input": _safe_json(input_json),
        "output": parsed_output,
        "stderr": stderr,
    }


def _resolve_runtime() -> str | None:
    if shutil.which("wasmtime"):
        return "wasmtime"
    if shutil.which("wasmer"):
        return "wasmer"
    return None


def _build_command(runtime: str, module_path: Path, input_json: str) -> list[str]:
    if runtime == "wasmtime":
        return ["wasmtime", module_path.as_posix(), input_json]
    return ["wasmer", "run", module_path.as_posix(), "--", input_json]


def _safe_json(text: str) -> object:
    try:
        return json.loads(text)
    except Exception:
        return text


def _missing_module_message(path: Path) -> str:
    return build_guidance_message(
        what="Wasm module file was not found.",
        why=f"Path does not exist: {path.as_posix()}.",
        fix="Build a wasm module first and pass the .wasm path.",
        example="n3 wasm run ./dist/demo/wasm/target/wasm32-wasip1/release/flow_runner.wasm --input '{}'",
    )


def _missing_runtime_message() -> str:
    return build_guidance_message(
        what="No wasm runtime was found.",
        why="n3 wasm run requires wasmtime or wasmer in PATH.",
        fix="Install wasmtime or wasmer, then retry.",
        example="n3 wasm run module.wasm --input '{}'",
    )


def _runtime_failed_message(runtime: str, detail: str) -> str:
    return build_guidance_message(
        what="Wasm execution failed.",
        why=f"{runtime} returned an error: {detail}.",
        fix="Verify module exports and input JSON.",
        example="n3 wasm run module.wasm --input '{\"a\":2,\"b\":3}'",
    )


__all__ = ["run_wasm_module"]
