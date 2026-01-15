from __future__ import annotations

from pathlib import Path

from namel3ss.config.loader import load_config
import json
from namel3ss.module_loader import load_project
from namel3ss.runtime.store.memory_store import MemoryStore
from namel3ss.validation_entrypoint import build_static_manifest


FIXTURE_PATH = Path("tests/fixtures/flow_declarative_app.ai")
MANIFEST_GOLDEN_PATH = Path("tests/fixtures/flow_declarative_manifest_golden.json")


def test_declarative_flow_manifest_golden(tmp_path: Path) -> None:
    source = FIXTURE_PATH.read_text(encoding="utf-8")
    app_file = tmp_path / "app.ai"
    app_file.write_text(source, encoding="utf-8")
    project = load_project(app_file)
    config = load_config(app_path=app_file)
    manifest = build_static_manifest(
        project.program,
        config=config,
        state={},
        store=MemoryStore(),
        warnings=[],
    )
    actual = json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    expected = MANIFEST_GOLDEN_PATH.read_text(encoding="utf-8")
    assert actual == expected
