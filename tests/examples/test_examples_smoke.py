from __future__ import annotations

import json
from pathlib import Path

from namel3ss.cli.main import main as cli_main

EXAMPLES = [
    "examples/demo_crud_dashboard.ai",
    "examples/demo_onboarding_flow.ai",
    "examples/demo_ai_assistant_over_records.ai",
]


def _run_cli(args: list[str]) -> int:
    return cli_main(args)


def test_examples_check_and_ui(tmp_path):
    for example in EXAMPLES:
        assert _run_cli([example, "check"]) == 0
        manifest_path = tmp_path / "manifest.json"
        with manifest_path.open("w", encoding="utf-8") as fh:
            # capture stdout via run ui -> redirect using cli_main printing
            pass
        ret = _run_cli([example, "ui"])
        assert ret == 0


def test_ui_manifest_has_pages_and_actions():
    from namel3ss.ir.nodes import lower_program
    from namel3ss.parser.core import parse
    from namel3ss.ui.manifest import build_manifest
    from namel3ss.runtime.store.memory_store import MemoryStore

    for example in EXAMPLES:
        source = Path(example).read_text(encoding="utf-8")
        ir = lower_program(parse(source))
        manifest = build_manifest(ir, state={}, store=MemoryStore())
        assert manifest.get("pages")
        assert manifest.get("actions") is not None
