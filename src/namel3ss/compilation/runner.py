from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from namel3ss.compilation.analysis import build_numeric_flow_plan
from namel3ss.compilation.codegen_c import generate_c_project
from namel3ss.compilation.codegen_python import generate_python_project
from namel3ss.compilation.codegen_rust import generate_rust_project
from namel3ss.compilation.config import load_compilation_config
from namel3ss.compilation.model import (
    CompiledModule,
    GeneratedProject,
    SUPPORTED_TARGETS,
    TARGET_C,
    TARGET_PYTHON,
    TARGET_RUST,
    TARGET_WASM,
)
from namel3ss.determinism import canonical_json_dump
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.module_loader import load_project


DEFAULT_COMPILED_DIR = ".namel3ss/compiled"


def compile_flow_to_target(
    *,
    app_path: Path,
    language: str,
    flow_name: str,
    out_dir: Path,
    build: bool,
) -> dict[str, object]:
    language_normalized = _normalize_language(language)
    project = load_project(app_path)
    plan = build_numeric_flow_plan(project.program, flow_name)

    if language_normalized == TARGET_C:
        generated = generate_c_project(plan, out_dir)
    elif language_normalized == TARGET_PYTHON:
        generated = generate_python_project(plan, out_dir)
    elif language_normalized == TARGET_RUST:
        generated = generate_rust_project(plan, out_dir, wasm=False)
    else:
        generated = generate_rust_project(plan, out_dir, wasm=True)

    if build and generated.build_command:
        _run_build(generated)
    source_only = generated.build_command is None or not build

    module = CompiledModule(
        flow_name=generated.flow_name,
        language=generated.language,
        artifact_path=generated.artifact.as_posix(),
        header_path=generated.header.as_posix() if generated.header else None,
        version="0.0.0",
        source_only=source_only,
    )
    metadata_path = generated.root / "compiled_module.json"
    canonical_json_dump(metadata_path, module.to_dict(), pretty=True, drop_run_keys=False)

    return {
        "ok": True,
        "flow_name": generated.flow_name,
        "language": generated.language,
        "root": generated.root.as_posix(),
        "artifact_path": generated.artifact.as_posix(),
        "header_path": generated.header.as_posix() if generated.header else None,
        "source_only": source_only,
        "metadata_path": metadata_path.as_posix(),
        "files": [path.as_posix() for path in generated.files],
        "build_command": list(generated.build_command) if generated.build_command else None,
    }


def list_compilation_targets(*, app_path: Path) -> dict[str, object]:
    config = load_compilation_config(project_root=app_path.parent, app_path=app_path)
    rows = [
        {
            "flow_name": name,
            "target": config.flows[name],
        }
        for name in sorted(config.flows.keys(), key=str)
    ]
    return {
        "ok": True,
        "count": len(rows),
        "items": rows,
    }


def clean_compiled_artifacts(*, app_path: Path, out_dir: Path) -> dict[str, object]:
    target = out_dir
    if not target.exists():
        return {
            "ok": True,
            "removed": False,
            "path": target.as_posix(),
            "files_removed": 0,
        }

    files_removed = 0
    if target.is_file():
        target.unlink()
        files_removed = 1
    else:
        files_removed = sum(1 for item in target.rglob("*") if item.is_file())
        shutil.rmtree(target)

    return {
        "ok": True,
        "removed": True,
        "path": target.as_posix(),
        "files_removed": files_removed,
    }


def default_output_dir(app_path: Path) -> Path:
    return app_path.parent / DEFAULT_COMPILED_DIR


def _normalize_language(value: str) -> str:
    text = str(value or "").strip().lower()
    if text in SUPPORTED_TARGETS:
        return text
    joined = ", ".join(SUPPORTED_TARGETS)
    raise Namel3ssError(
        build_guidance_message(
            what=f"Unsupported language '{text or '<empty>'}'.",
            why=f"Compile supports {joined}.",
            fix="Choose one supported language target.",
            example="n3 compile --lang rust --flow demo",
        )
    )


def _run_build(generated: GeneratedProject) -> None:
    if not generated.build_command:
        return
    executable = generated.build_command[0]
    if shutil.which(executable) is None:
        raise Namel3ssError(
            build_guidance_message(
                what=f"Build tool '{executable}' is not available.",
                why="The selected language target requires local toolchain support.",
                fix=f"Install {executable} or run compile without --build.",
                example="n3 compile --lang rust --flow demo",
            )
        )
    result = subprocess.run(
        list(generated.build_command),
        cwd=generated.root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        details = result.stderr.strip() or result.stdout.strip() or "unknown build error"
        raise Namel3ssError(
            build_guidance_message(
                what="Compiled module build failed.",
                why=details,
                fix="Fix compile errors in the generated project and retry.",
                example=f"cd {generated.root.as_posix()} && {' '.join(generated.build_command)}",
            )
        )
    if not generated.artifact.exists():
        raise Namel3ssError(
            build_guidance_message(
                what="Build completed but artifact is missing.",
                why=f"Expected artifact at {generated.artifact.as_posix()}.",
                fix="Re-run the build command in the generated project directory.",
                example=f"cd {generated.root.as_posix()} && {' '.join(generated.build_command)}",
            )
        )


__all__ = [
    "DEFAULT_COMPILED_DIR",
    "clean_compiled_artifacts",
    "compile_flow_to_target",
    "default_output_dir",
    "list_compilation_targets",
]
