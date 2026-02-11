from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
import tempfile


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
sys.dont_write_bytecode = True
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

from namel3ss.config.loader import load_config
from namel3ss.determinism import canonical_json_dumps
from namel3ss.ingestion.policy import ACTION_RETRIEVAL_INCLUDE_WARN, PolicyDecision
from namel3ss.module_loader import load_project
from namel3ss.retrieval.api import run_retrieval
from namel3ss.validation_entrypoint import build_static_manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Deterministic repeat-run checks for compose + retrieval trace.")
    parser.add_argument("target", nargs="?", default=None, help="Root app.ai path.")
    parser.add_argument("--check", action="store_true", help="Run determinism checks and return non-zero on drift.")
    args = parser.parse_args()

    app_path = _resolve_app_for_check(args.target)
    if app_path is None:
        print("Unable to resolve deterministic check app path.", file=sys.stderr)
        return 1
    if not _check_manifest_repeatability(app_path):
        return 1
    if not _check_retrieval_trace_repeatability():
        return 1
    print("Determinism repeat checks passed.")
    return 0


def _resolve_app_for_check(target: str | None) -> Path | None:
    if target:
        app_path = Path(target).resolve()
        if app_path.exists():
            return app_path
        return None
    candidate = Path("app.ai").resolve()
    if candidate.exists():
        return candidate
    root = Path(tempfile.mkdtemp(prefix="n3_determinism_")).resolve()
    app_file = root / "app.ai"
    include_dir = root / "modules"
    include_dir.mkdir(parents=True, exist_ok=True)
    app_file.write_text(
        """
spec is "1.0"

capabilities:
  composition.includes

include "modules/flow.ai"

flow "root_main":
  return "ok"

page "home":
  title is "Determinism"
""".lstrip(),
        encoding="utf-8",
    )
    (include_dir / "flow.ai").write_text(
        """
flow "helper":
  return "helper"
""".lstrip(),
        encoding="utf-8",
    )
    return app_file


def _check_manifest_repeatability(app_path: Path) -> bool:
    project_one = load_project(app_path)
    project_two = load_project(app_path)
    config = load_config(app_path=app_path)
    manifest_one = build_static_manifest(project_one.program, config=config, state={}, store=None, warnings=[])
    manifest_two = build_static_manifest(project_two.program, config=config, state={}, store=None, warnings=[])
    left = canonical_json_dumps(manifest_one, pretty=False, drop_run_keys=False)
    right = canonical_json_dumps(manifest_two, pretty=False, drop_run_keys=False)
    if left != right:
        print("Repeat compile mismatch: manifest bytes changed.", file=sys.stderr)
        return False
    return True


def _check_retrieval_trace_repeatability() -> bool:
    state = {
        "retrieval": {"tuning": {"semantic_weight": 0.5, "semantic_k": 8, "lexical_k": 8, "final_top_k": 8}},
        "ingestion": {"doc-a": {"status": "pass"}, "doc-b": {"status": "pass"}},
        "index": {
            "chunks": [
                {
                    "upload_id": "doc-a",
                    "chunk_id": "doc-a:0",
                    "document_id": "doc-a",
                    "source_name": "Doc A",
                    "page_number": 1,
                    "chunk_index": 0,
                    "ingestion_phase": "deep",
                    "keywords": ["alpha", "billing"],
                    "text": "alpha billing",
                    "tags": ["billing"],
                },
                {
                    "upload_id": "doc-b",
                    "chunk_id": "doc-b:0",
                    "document_id": "doc-b",
                    "source_name": "Doc B",
                    "page_number": 1,
                    "chunk_index": 1,
                    "ingestion_phase": "deep",
                    "keywords": ["alpha", "support"],
                    "text": "alpha support",
                    "tags": ["support"],
                },
            ]
        },
    }
    decision = PolicyDecision(
        action=ACTION_RETRIEVAL_INCLUDE_WARN,
        allowed=True,
        reason="determinism-check",
        required_permissions=(),
        source="tool",
    )
    first = run_retrieval(
        query="alpha",
        state=state,
        project_root=None,
        app_path=None,
        policy_decision=decision,
        diagnostics_trace_enabled=True,
    )
    second = run_retrieval(
        query="alpha",
        state=state,
        project_root=None,
        app_path=None,
        policy_decision=decision,
        diagnostics_trace_enabled=True,
    )
    left = canonical_json_dumps(first.get("retrieval_trace_diagnostics") or {}, pretty=False, drop_run_keys=False)
    right = canonical_json_dumps(second.get("retrieval_trace_diagnostics") or {}, pretty=False, drop_run_keys=False)
    if left != right:
        print("Repeat retrieval trace mismatch: trace payload changed.", file=sys.stderr)
        return False
    return True


if __name__ == "__main__":
    raise SystemExit(main())
