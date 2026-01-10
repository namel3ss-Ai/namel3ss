from __future__ import annotations

import json
import shutil
from pathlib import Path

from namel3ss.cli.app_loader import load_program
from namel3ss.config.loader import load_config
from namel3ss.runtime.errors.explain.collect import collect_last_error
from namel3ss.runtime.run_pipeline import build_flow_payload, finalize_run_payload
from namel3ss.runtime.store.memory_store import MemoryStore
from namel3ss.runtime.tools.bindings import load_tool_bindings, write_tool_bindings
from namel3ss.runtime.tools.bindings_yaml import ToolBinding
from namel3ss.secrets import collect_secret_values

PATTERN_ROOT = Path(__file__).resolve().parents[2] / "patterns" / "agents" / "research_agentic_rag"


def _stage_pattern(tmp_path: Path) -> Path:
    target = tmp_path / "research_agentic_rag"
    shutil.copytree(PATTERN_ROOT, target)
    return target


def _load_app(app_dir: Path):
    app_path = app_dir / "app.ai"
    program, _ = load_program(app_path.as_posix())
    config = load_config(app_path=app_path, root=app_dir)
    return app_path, program, config


def _write_last_run(app_dir: Path, payload: dict) -> None:
    run_dir = app_dir / ".namel3ss" / "run"
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / "last.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _run_flow(
    app_dir: Path,
    program,
    config,
    *,
    flow_name: str = "research_demo",
    identity: dict,
    store: MemoryStore,
    input_payload: dict | None = None,
    state: dict | None = None,
):
    outcome = build_flow_payload(
        program,
        flow_name,
        state=state,
        input=input_payload,
        store=store,
        config=config,
        identity=identity,
        project_root=app_dir,
    )
    payload = finalize_run_payload(outcome.payload, collect_secret_values(config))
    _write_last_run(app_dir, payload)
    return outcome, payload


def _schema(program, name: str):
    return next(schema for schema in program.records if schema.name == name)


def _write_tool(app_dir: Path, filename: str, body: str) -> None:
    tools_dir = app_dir / "tools"
    tools_dir.mkdir(exist_ok=True)
    (tools_dir / filename).write_text(body, encoding="utf-8")


def _override_tool_entry(app_dir: Path, tool_name: str, entry: str) -> None:
    bindings = load_tool_bindings(app_dir)
    existing = bindings.get(tool_name)
    if existing is None:
        bindings[tool_name] = ToolBinding(kind="python", entry=entry)
    else:
        bindings[tool_name] = ToolBinding(
            kind=existing.kind,
            entry=entry,
            runner=existing.runner,
            url=existing.url,
            image=existing.image,
            command=existing.command,
            env=existing.env,
            purity=existing.purity,
            timeout_ms=existing.timeout_ms,
            sandbox=existing.sandbox,
            enforcement=existing.enforcement,
        )
    write_tool_bindings(app_dir, bindings)


def test_research_agentic_rag_success_path(tmp_path: Path) -> None:
    app_dir = _stage_pattern(tmp_path)
    _, program, config = _load_app(app_dir)
    store = MemoryStore()
    query = "Tested query input"
    outcome, _payload = _run_flow(
        app_dir,
        program,
        config,
        identity={"email": "researcher@example.com", "role": "researcher"},
        store=store,
        input_payload={"query": query},
    )
    assert outcome.error is None

    results = store.list_records(_schema(program, "ResearchResult"), limit=50)
    citations = store.list_records(_schema(program, "Citation"), limit=50)
    assert results
    assert citations

    assert results[0].get("query") == query
    summary = results[0].get("summary")
    assert isinstance(summary, str) and summary.strip()
    for citation in citations:
        assert isinstance(citation.get("title"), str) and citation["title"].strip()
        assert isinstance(citation.get("url"), str) and citation["url"].strip()
        assert isinstance(citation.get("snippet"), str) and citation["snippet"].strip()


def test_research_agentic_rag_no_sources(tmp_path: Path) -> None:
    app_dir = _stage_pattern(tmp_path)
    _write_tool(
        app_dir,
        "retrieve_docs_empty.py",
        "def run(payload: dict) -> dict:\n"
        "    return {\"documents\": []}\n",
    )
    _override_tool_entry(app_dir, "retrieve docs", "tools.retrieve_docs_empty:run")

    _, program, config = _load_app(app_dir)
    store = MemoryStore()
    outcome, payload = _run_flow(
        app_dir,
        program,
        config,
        identity={"email": "researcher@example.com", "role": "researcher"},
        store=store,
        input_payload={"query": "No sources query"},
    )
    assert outcome.error is None
    assert payload.get("result") == "no_sources"
    assert store.list_records(_schema(program, "ResearchResult"), limit=20) == []
    assert store.list_records(_schema(program, "Citation"), limit=20) == []


def test_research_agentic_rag_clear_results(tmp_path: Path) -> None:
    app_dir = _stage_pattern(tmp_path)
    _, program, config = _load_app(app_dir)
    store = MemoryStore()
    query = "Clearable query"
    outcome, _payload = _run_flow(
        app_dir,
        program,
        config,
        identity={"email": "researcher@example.com", "role": "researcher"},
        store=store,
        input_payload={"query": query},
    )
    assert outcome.error is None
    assert store.list_records(_schema(program, "ResearchResult"), limit=20)
    state = store.load_state()
    outcome, payload = _run_flow(
        app_dir,
        program,
        config,
        flow_name="clear_results",
        identity={"email": "researcher@example.com", "role": "researcher"},
        store=store,
        state=state,
    )
    assert outcome.error is None
    assert payload.get("result") == "cleared"
    assert store.list_records(_schema(program, "ResearchResult"), limit=20) == []
    assert store.list_records(_schema(program, "Citation"), limit=20) == []


def test_research_agentic_rag_empty_query_validation(tmp_path: Path) -> None:
    app_dir = _stage_pattern(tmp_path)
    _, program, config = _load_app(app_dir)
    store = MemoryStore()
    outcome, payload = _run_flow(
        app_dir,
        program,
        config,
        identity={"email": "researcher@example.com", "role": "researcher"},
        store=store,
        input_payload={"query": ""},
    )
    assert outcome.error is None
    assert payload.get("result") == "invalid_query"
    assert store.list_records(_schema(program, "ResearchResult"), limit=20) == []
    assert store.list_records(_schema(program, "Citation"), limit=20) == []


def test_research_agentic_rag_permission_gate(tmp_path: Path) -> None:
    app_dir = _stage_pattern(tmp_path)
    _, program, config = _load_app(app_dir)
    store = MemoryStore()
    outcome, _payload = _run_flow(
        app_dir,
        program,
        config,
        identity={"email": "viewer@example.com", "role": "viewer"},
        store=store,
    )
    assert outcome.error is not None
    error_state = collect_last_error(app_dir)
    assert error_state is not None
    assert error_state.kind == "permission"
    assert store.list_records(_schema(program, "ResearchResult"), limit=20) == []
    assert store.list_records(_schema(program, "Citation"), limit=20) == []
