from __future__ import annotations

import json
import tempfile
from pathlib import Path

from namel3ss.determinism import canonical_json_dumps
from namel3ss.ir.nodes import lower_program
from namel3ss.parser.core import parse
from namel3ss.runtime.store.memory_store import MemoryStore
from namel3ss.ui.manifest import build_manifest
from tests.conftest import run_flow
from tests.golden.harness import load_manifest, run_golden_app
from tests.spec_freeze.helpers.ast_dump import dump_ast
from tests.spec_freeze.helpers.ir_dump import dump_ir
from tests.spec_freeze.helpers.runtime_dump import dump_runtime
from tests.spec_freeze.helpers.runtime_samples import runtime_sources
from tests.spec_freeze.helpers.samples import sample_sources
from tests.ui.ui_manifest_baseline_harness import (
    BASELINE_FIXTURES_DIR,
    baseline_cases,
    build_case_snapshot,
)


UI_LAYOUT_FIXTURE = Path("tests/fixtures/ui_layout_manifest_app.ai")
UI_LAYOUT_GOLDEN = Path("tests/fixtures/ui_layout_manifest_golden.json")
UI_LAYOUT_STATE = {
    "show_top": True,
    "show_main": False,
    "show_drawer": True,
}

UI_THEME_FIXTURE = Path("tests/fixtures/ui_theme_manifest_app.ai")
UI_THEME_GOLDEN = Path("tests/fixtures/ui_theme_manifest_golden.json")
UI_THEME_STATE = {
    "ui": {
        "settings": {
            "size": "normal",
            "radius": "lg",
        }
    }
}

RAG_UI_FIXTURE = Path("tests/fixtures/rag_ui_manifest_app.ai")
RAG_UI_GOLDEN = Path("tests/fixtures/rag_ui_manifest_golden.json")
RAG_UI_STATE = {
    "chat": {
        "messages": [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ],
        "citations": [
            {
                "title": "Doc A",
                "url": "https://example.com",
                "snippet": "Example snippet",
            }
        ],
    },
    "loading": False,
    "ui": {
        "show_drawer": True,
        "preview_source": {
            "title": "Doc A",
            "url": "https://example.com",
            "snippet": "Example snippet",
        },
    },
}

CORE_EXAMPLES_DIR = Path("tests/fixtures/core_examples")
CORE_PARSER_DIR = CORE_EXAMPLES_DIR / "parser"
CORE_IR_DIR = CORE_EXAMPLES_DIR / "ir"
CORE_RUNTIME_DIR = CORE_EXAMPLES_DIR / "runtime"
GOLDEN_SNAPSHOTS_DIR = Path("tests/fixtures/golden_snapshots")

ALLOWED_TARGET_DIRS: tuple[Path, ...] = (
    BASELINE_FIXTURES_DIR,
    GOLDEN_SNAPSHOTS_DIR,
    CORE_EXAMPLES_DIR,
)
ALLOWED_TARGET_FILES: tuple[Path, ...] = (
    UI_LAYOUT_GOLDEN,
    UI_THEME_GOLDEN,
    RAG_UI_GOLDEN,
)
ALLOWED_TARGET_GLOBS: tuple[str, ...] = (
    "tests/fixtures/ui_*_manifest_golden.json",
)

RUNTIME_IDENTITY = {
    "id": "user-1",
    "trust_level": "contributor",
}


def build_baseline_payloads() -> dict[Path, str]:
    payloads: dict[Path, str] = {}
    payloads.update(_ui_manifest_baseline_payloads())
    payloads.update(_ui_manifest_golden_payloads())
    payloads.update(_golden_snapshot_payloads())
    payloads.update(_core_examples_payloads())
    _validate_targets(payloads)
    return {path: payloads[path] for path in sorted(payloads, key=lambda item: item.as_posix())}


def is_allowed_target(path: Path) -> bool:
    normalized = Path(path.as_posix())
    if normalized in ALLOWED_TARGET_FILES:
        return True
    if any(normalized.match(pattern) for pattern in ALLOWED_TARGET_GLOBS):
        return True
    return any(_is_under(normalized, root) for root in ALLOWED_TARGET_DIRS)


def allowed_target_roots() -> tuple[Path, ...]:
    return ALLOWED_TARGET_DIRS


def _ui_manifest_baseline_payloads() -> dict[Path, str]:
    payloads: dict[Path, str] = {}
    for case in baseline_cases():
        snapshot = build_case_snapshot(case)
        path = BASELINE_FIXTURES_DIR / f"{case.name}.json"
        payloads[path] = canonical_json_dumps(snapshot, pretty=True, drop_run_keys=False)
    return payloads


def _ui_manifest_golden_payloads() -> dict[Path, str]:
    layout_manifest = _build_manifest_from_fixture(UI_LAYOUT_FIXTURE, state=UI_LAYOUT_STATE)
    theme_manifest = _build_manifest_from_fixture(UI_THEME_FIXTURE, state=UI_THEME_STATE)
    rag_manifest = _build_manifest_from_fixture(RAG_UI_FIXTURE, state=RAG_UI_STATE)
    return {
        UI_LAYOUT_GOLDEN: canonical_json_dumps(layout_manifest, pretty=True, drop_run_keys=False),
        UI_THEME_GOLDEN: canonical_json_dumps(theme_manifest, pretty=True, drop_run_keys=False),
        RAG_UI_GOLDEN: canonical_json_dumps(rag_manifest, pretty=True, drop_run_keys=False),
    }


def _golden_snapshot_payloads() -> dict[Path, str]:
    payloads: dict[Path, str] = {}
    with tempfile.TemporaryDirectory(prefix="namel3ss-ui-golden-") as raw_tmp:
        tmp_root = Path(raw_tmp)
        for app in load_manifest():
            snapshot = run_golden_app(app, tmp_root / app.app_id)
            base = GOLDEN_SNAPSHOTS_DIR / app.app_id
            payloads[base / "ir.json"] = _pretty_json(snapshot["ir"])
            payloads[base / "run.json"] = _pretty_json(snapshot["run"])
            payloads[base / "traces.json"] = _pretty_json(snapshot["traces"])
            payloads[base / "hashes.json"] = _pretty_json(snapshot["hashes"])
    return payloads


def _core_examples_payloads() -> dict[Path, str]:
    payloads: dict[Path, str] = {}
    for name, _path, source in sample_sources():
        ast_program = parse(source)
        ir_program = lower_program(parse(source))
        payloads[CORE_PARSER_DIR / f"{name}.json"] = _pretty_json(dump_ast(ast_program))
        payloads[CORE_IR_DIR / f"{name}.json"] = _pretty_json(dump_ir(ir_program))

    with tempfile.TemporaryDirectory(prefix="namel3ss-core-runtime-") as raw_tmp:
        tmp_root = Path(raw_tmp)
        for name, _path, flow_name, source in runtime_sources():
            runtime_root = tmp_root / name
            runtime_root.mkdir(parents=True, exist_ok=True)
            result = run_flow(
                source,
                flow_name=flow_name,
                initial_state={},
                store=MemoryStore(),
                identity=dict(RUNTIME_IDENTITY),
                project_root=runtime_root,
                app_path=runtime_root / "app.ai",
            )
            payloads[CORE_RUNTIME_DIR / f"{name}.json"] = _pretty_json(dump_runtime(result))
    return payloads


def _build_manifest_from_fixture(path: Path, *, state: dict) -> dict:
    source = path.read_text(encoding="utf-8")
    program = lower_program(parse(source))
    return build_manifest(program, state=dict(state), store=None)


def _pretty_json(value: object) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def _validate_targets(payloads: dict[Path, str]) -> None:
    invalid = sorted(
        path.as_posix()
        for path in payloads
        if not is_allowed_target(path)
    )
    if invalid:
        joined = "\n".join(invalid)
        raise RuntimeError(f"Baseline target outside allowlist:\n{joined}")


def _is_under(path: Path, root: Path) -> bool:
    if path == root:
        return True
    return root in path.parents


__all__ = [
    "ALLOWED_TARGET_DIRS",
    "ALLOWED_TARGET_FILES",
    "ALLOWED_TARGET_GLOBS",
    "allowed_target_roots",
    "build_baseline_payloads",
    "is_allowed_target",
]
