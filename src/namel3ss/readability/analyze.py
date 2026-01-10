from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.module_loader.source_io import _parse_source, _read_source
from namel3ss.readability.counter import FlowCounter
from namel3ss.readability.model import (
    ComplexityCounts,
    FileReport,
    FlowReport,
    IntentCounts,
    OffenderCount,
    PlumbingCounts,
    ReadabilityReport,
    Scorecard,
    ScoreInputs,
    UIFlowBinding,
)

_SCORE_FORMULA = "score = 100 - (plumbing_weighted * 3) - (structure_ops * 4) - (branches * 2) - (indent_depth * 2)"
_SCORE_WEIGHTS = {
    "plumbing_weighted": 3,
    "structure_ops": 4,
    "branches": 2,
    "indent_depth": 2,
}
_TOP_OFFENDERS_LIMIT = 5
_OFFENDER_KEYS = (
    "ask_ai_count",
    "comparisons_count",
    "create_count",
    "delete_count",
    "find_count",
    "index_pattern_count",
    "let_count",
    "list_get_count",
    "list_length_count",
    "list_op_count",
    "map_get_count",
    "map_op_count",
    "run_agent_count",
    "run_agents_parallel_count",
    "state_write_count",
    "try_catch_count",
    "ui_binding_count",
    "update_count",
)

def analyze_path(path: Path) -> ReadabilityReport:
    target = Path(path)
    if not target.exists():
        raise Namel3ssError(
            build_guidance_message(
                what=f"Path not found: {target.as_posix()}",
                why="Readability requires an existing .ai file or a folder containing .ai files.",
                fix="Pass a valid file or folder path.",
                example="n3 readability app.ai",
            )
        )
    files = _collect_ai_files(target)
    return analyze_files(files, analyzed_path=_display_path(target))

def analyze_files(files: list[Path], *, analyzed_path: str = "multiple") -> ReadabilityReport:
    if not files:
        raise Namel3ssError(
            build_guidance_message(
                what="No .ai files found to analyze.",
                why="Readability needs at least one .ai file.",
                fix="Pass a .ai file or a folder containing .ai files.",
                example="n3 readability examples/demo_multi_agent_orchestration.ai",
            )
        )
    sorted_files = sorted({path.resolve() for path in files}, key=lambda p: p.as_posix())
    file_reports: list[FileReport] = []
    flow_count = 0
    for path in sorted_files:
        file_report = _analyze_file(path)
        flow_count += file_report.flow_count
        file_reports.append(file_report)
    return ReadabilityReport(
        schema_version=1,
        analyzed_path=analyzed_path,
        score_formula=_SCORE_FORMULA,
        score_weights=_SCORE_WEIGHTS,
        file_count=len(file_reports),
        flow_count=flow_count,
        files=file_reports,
    )

def render_json(report: ReadabilityReport) -> str:
    payload = asdict(report)
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n"

def render_text(report: ReadabilityReport) -> str:
    lines: list[str] = []
    lines.append(f"Readability report for {report.analyzed_path}")
    lines.append(f"Files: {report.file_count} | Flows: {report.flow_count}")
    lines.append(f"Score formula: {report.score_formula}")
    lines.append("")
    for file_report in report.files:
        lines.append(file_report.path)
        lines.append(f"  flows: {file_report.flow_count}")
        lines.append(f"  record must constraints: {file_report.record_constraints_must}")
        lines.append(f"  ui button bindings: {file_report.ui_button_bindings_total}")
        for binding in file_report.ui_button_bindings:
            lines.append(f"    button -> {binding.flow}: {binding.count}")
        lines.append("  Top offenders:")
        if file_report.top_offenders:
            for offender in file_report.top_offenders:
                lines.append(f"    {offender.name}={offender.count}")
        else:
            lines.append("    none")
        for flow in file_report.flows:
            lines.append(f"  flow {flow.name}")
            lines.append(f"    heatline: {_format_heatline(flow)}")
            lines.append(f"    score inputs: {_format_score_inputs(flow.scorecard.score_inputs)}")
            lines.append("    Top offenders:")
            if flow.top_offenders:
                for offender in flow.top_offenders:
                    lines.append(f"      {offender.name}={offender.count}")
            else:
                lines.append("      none")
            lines.append(
                "    plumbing: "
                f"find={flow.plumbing.find} delete={flow.plumbing.delete} "
                f"create={flow.plumbing.create} update={flow.plumbing.update} "
                f"save={flow.plumbing.save} set_state={flow.plumbing.set_state} "
                f"try_catch={flow.plumbing.try_catch} list_get={flow.plumbing.list_get} "
                f"list_length={flow.plumbing.list_length} map_get={flow.plumbing.map_get} "
                f"index_patterns={flow.plumbing.index_patterns}"
            )
            lines.append(
                "    intent: "
                f"ask_ai={flow.intent.ask_ai} run_agent={flow.intent.run_agent} "
                f"run_parallel={flow.intent.run_parallel} comparisons={flow.intent.comparisons} "
                f"ui_button_calls={flow.intent.ui_button_calls} "
                f"record_constraints_must={flow.intent.record_constraints_must}"
            )
            lines.append(
                "    complexity: "
                f"branches={flow.complexity.branches} max_depth={flow.complexity.max_depth} "
                f"record_refs={flow.complexity.record_refs} "
                f"state_writes={flow.complexity.distinct_state_writes}"
            )
        lines.append("")
    lines.extend(_format_roadmap_mapping(report))
    return "\n".join(lines).rstrip()

def _collect_ai_files(path: Path) -> list[Path]:
    if path.is_file():
        if path.suffix != ".ai":
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Unsupported file type: {path.as_posix()}",
                    why="Readability only accepts .ai files.",
                    fix="Pass a .ai file or a folder containing .ai files.",
                    example="n3 readability app.ai",
                )
            )
        return [path]
    if not path.is_dir():
        raise Namel3ssError(
            build_guidance_message(
                what=f"Unsupported path: {path.as_posix()}",
                why="Readability expects a file or directory.",
                fix="Pass a .ai file or a folder containing .ai files.",
                example="n3 readability examples",
            )
        )
    files = [
        file
        for file in path.rglob("*.ai")
        if file.is_file() and not _is_hidden_path(file)
    ]
    if not files:
        raise Namel3ssError(
            build_guidance_message(
                what=f"No .ai files found under {path.as_posix()}",
                why="The folder does not contain any .ai sources.",
                fix="Point to a folder with .ai files or pass a file directly.",
                example="n3 readability examples/demo_multi_agent_orchestration.ai",
            )
        )
    return files

def _is_hidden_path(path: Path) -> bool:
    return any(part.startswith(".") for part in path.parts)

def _display_path(path: Path) -> str:
    resolved = path.resolve()
    base = Path.cwd().resolve()
    try:
        return resolved.relative_to(base).as_posix()
    except ValueError:
        return resolved.as_posix()

def _analyze_file(path: Path) -> FileReport:
    source = _read_source(path, None)
    program = _parse_source(
        source,
        path,
        allow_legacy_type_aliases=True,
        allow_capsule=path.name == "capsule.ai",
        require_spec=False,
        lower_sugar=False,
    )
    ui_bindings = _collect_ui_button_calls(program.pages)
    ui_record_bindings = _count_ui_record_bindings(program.pages)
    binding_list = [UIFlowBinding(flow=name, count=count) for name, count in sorted(ui_bindings.items())]
    ui_total = sum(ui_bindings.values())
    record_constraints = _count_record_constraints(program.records)
    file_offenders = _empty_offender_counts()
    flow_reports: list[FlowReport] = []
    for flow in sorted(program.flows, key=lambda f: f.name):
        flow_report, offender_counts = _analyze_flow(flow, ui_bindings, record_constraints)
        _merge_offender_counts(file_offenders, offender_counts)
        flow_reports.append(flow_report)
    file_offenders["ui_binding_count"] += ui_record_bindings
    file_top_offenders = _sorted_offenders(file_offenders, limit=_TOP_OFFENDERS_LIMIT)
    return FileReport(
        path=_display_path(path),
        flow_count=len(flow_reports),
        record_constraints_must=record_constraints,
        ui_button_bindings_total=ui_total,
        ui_button_bindings=binding_list,
        flows=flow_reports,
        top_offenders=file_top_offenders,
    )

def _count_record_constraints(records: list[ast.RecordDecl]) -> int:
    count = 0
    for record in records:
        for field in record.fields:
            if field.constraint is not None:
                count += 1
    return count

def _collect_ui_button_calls(pages: list[ast.PageDecl]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for page in pages:
        for item in page.items:
            _walk_page_item(item, counts)
    return counts

def _walk_page_item(item: ast.PageItem, counts: dict[str, int]) -> None:
    if isinstance(item, ast.ButtonItem):
        counts[item.flow_name] = counts.get(item.flow_name, 0) + 1
        return
    if isinstance(item, ast.TabsItem):
        for tab in item.tabs:
            for child in tab.children:
                _walk_page_item(child, counts)
        return
    children = getattr(item, "children", None)
    if isinstance(children, list):
        for child in children:
            _walk_page_item(child, counts)

def _count_ui_record_bindings(pages: list[ast.PageDecl]) -> int:
    total = 0
    for page in pages:
        for item in page.items:
            total += _walk_record_bindings(item)
    return total

def _walk_record_bindings(item: ast.PageItem) -> int:
    total = 0
    record_name = getattr(item, "record_name", None)
    if isinstance(record_name, str):
        total += 1
    if isinstance(item, ast.TabsItem):
        for tab in item.tabs:
            for child in tab.children:
                total += _walk_record_bindings(child)
        return total
    children = getattr(item, "children", None)
    if isinstance(children, list):
        for child in children:
            total += _walk_record_bindings(child)
    return total

def _analyze_flow(
    flow: ast.Flow,
    ui_bindings: dict[str, int],
    record_constraints_must: int,
) -> tuple[FlowReport, dict[str, int]]:
    counter = FlowCounter()
    for stmt in flow.body:
        counter.walk_statement(stmt, depth=1)

    plumbing_statement_ops = (
        counter.find
        + counter.delete
        + counter.create
        + counter.update
        + counter.save
        + counter.set_state
        + counter.try_catch
    )
    structure_ops = counter.list_get + counter.list_length + counter.map_get + counter.index_patterns
    plumbing_total = plumbing_statement_ops + structure_ops
    statement_count = counter.statement_total
    plumbing_ratio = plumbing_total / max(statement_count, 1)

    score = 100
    score -= plumbing_statement_ops * _SCORE_WEIGHTS["plumbing_weighted"]
    score -= structure_ops * _SCORE_WEIGHTS["structure_ops"]
    score -= counter.branches * _SCORE_WEIGHTS["branches"]
    score -= counter.max_depth * _SCORE_WEIGHTS["indent_depth"]
    score = max(0, min(100, score))

    ui_button_calls = ui_bindings.get(flow.name, 0)
    intent_total = counter.ask_ai + counter.run_agent + counter.run_parallel + counter.comparisons + ui_button_calls + record_constraints_must
    offender_counts = _build_offender_counts(counter, ui_button_calls)
    top_offenders = _sorted_offenders(offender_counts, limit=_TOP_OFFENDERS_LIMIT)
    score_inputs = ScoreInputs(
        plumbing_weighted=plumbing_statement_ops,
        structure_ops=structure_ops,
        branches=counter.branches,
        indent_depth=counter.max_depth,
    )

    return FlowReport(
        name=flow.name,
        statement_count=statement_count,
        plumbing_ratio=round(plumbing_ratio, 3),
        plumbing=PlumbingCounts(
            find=counter.find,
            delete=counter.delete,
            create=counter.create,
            update=counter.update,
            save=counter.save,
            set_state=counter.set_state,
            try_catch=counter.try_catch,
            list_get=counter.list_get,
            list_length=counter.list_length,
            map_get=counter.map_get,
            index_patterns=counter.index_patterns,
            statement_ops=plumbing_statement_ops,
            structure_ops=structure_ops,
            total=plumbing_total,
        ),
        intent=IntentCounts(
            ask_ai=counter.ask_ai,
            run_agent=counter.run_agent,
            run_parallel=counter.run_parallel,
            comparisons=counter.comparisons,
            ui_button_calls=ui_button_calls,
            record_constraints_must=record_constraints_must,
            total=intent_total,
        ),
        complexity=ComplexityCounts(
            branches=counter.branches,
            max_depth=counter.max_depth,
            record_refs=len(counter.record_refs),
            distinct_state_writes=len(counter.state_paths),
        ),
        scorecard=Scorecard(
            score=score,
            plumbing_ratio=round(plumbing_ratio, 3),
            plumbing_weighted=plumbing_statement_ops,
            structure_ops=structure_ops,
            branches=counter.branches,
            indent_depth=counter.max_depth,
            score_inputs=score_inputs,
        ),
        top_offenders=top_offenders,
    ), offender_counts

def _empty_offender_counts() -> dict[str, int]:
    return {key: 0 for key in _OFFENDER_KEYS}

def _build_offender_counts(counter: FlowCounter, ui_binding_count: int) -> dict[str, int]:
    counts = _empty_offender_counts()
    counts.update(
        {
            "ask_ai_count": counter.ask_ai,
            "comparisons_count": counter.comparisons,
            "create_count": counter.create,
            "delete_count": counter.delete,
            "find_count": counter.find,
            "index_pattern_count": counter.index_patterns,
            "let_count": counter.let_count,
            "list_get_count": counter.list_get,
            "list_length_count": counter.list_length,
            "list_op_count": counter.list_op_total,
            "map_get_count": counter.map_get,
            "map_op_count": counter.map_op_total,
            "run_agent_count": counter.run_agent,
            "run_agents_parallel_count": counter.run_parallel,
            "state_write_count": counter.set_state,
            "try_catch_count": counter.try_catch,
            "ui_binding_count": ui_binding_count,
            "update_count": counter.update,
        }
    )
    return counts

def _merge_offender_counts(base: dict[str, int], incoming: dict[str, int]) -> None:
    for key in _OFFENDER_KEYS:
        base[key] += incoming.get(key, 0)

def _sorted_offenders(counts: dict[str, int], *, limit: int | None) -> list[OffenderCount]:
    items = [(name, count) for name, count in counts.items() if count > 0]
    items.sort(key=lambda item: (-item[1], item[0]))
    if limit is not None:
        items = items[:limit]
    return [OffenderCount(name=name, count=count) for name, count in items]

def _format_heatline(flow: FlowReport) -> str:
    counts = {
        "find": flow.plumbing.find,
        "delete": flow.plumbing.delete,
        "create": flow.plumbing.create,
        "update": flow.plumbing.update,
        "list_get": flow.plumbing.list_get,
        "list_length": flow.plumbing.list_length,
        "map_get": flow.plumbing.map_get,
        "state_writes": flow.plumbing.set_state,
        "try_catch": flow.plumbing.try_catch,
        "index_math": flow.plumbing.index_patterns,
    }
    items = [(name, count) for name, count in counts.items() if count > 0]
    items.sort(key=lambda item: (-item[1], item[0]))
    top_items = items[:_TOP_OFFENDERS_LIMIT]
    top_text = "none" if not top_items else " ".join(f"{name}={count}" for name, count in top_items)
    return (
        f"score {flow.scorecard.score}, plumbing_ratio {flow.plumbing_ratio:.2f} "
        f"({flow.plumbing.total}/{flow.statement_count}), top: {top_text}"
    )

def _format_score_inputs(inputs: ScoreInputs) -> str:
    return (
        f"plumbing_weighted={inputs.plumbing_weighted} "
        f"structure_ops={inputs.structure_ops} "
        f"branches={inputs.branches} "
        f"indent_depth={inputs.indent_depth}"
    )

def _format_roadmap_mapping(report: ReadabilityReport) -> list[str]:
    totals = {
        "find": 0,
        "list_length": 0,
        "list_get": 0,
        "index_math": 0,
        "set_state": 0,
        "create": 0,
        "delete": 0,
        "map_get": 0,
        "try_catch": 0,
        "run_agent": 0,
        "run_parallel": 0,
    }
    for file_report in report.files:
        for flow in file_report.flows:
            totals["find"] += flow.plumbing.find
            totals["list_length"] += flow.plumbing.list_length
            totals["list_get"] += flow.plumbing.list_get
            totals["index_math"] += flow.plumbing.index_patterns
            totals["set_state"] += flow.plumbing.set_state
            totals["create"] += flow.plumbing.create
            totals["delete"] += flow.plumbing.delete
            totals["map_get"] += flow.plumbing.map_get
            totals["try_catch"] += flow.plumbing.try_catch
            totals["run_agent"] += flow.intent.run_agent
            totals["run_parallel"] += flow.intent.run_parallel
    retrieval_total = totals["find"] + totals["list_length"] + totals["list_get"] + totals["index_math"]
    storage_total = totals["set_state"] + totals["create"] + totals["delete"]
    data_access_total = totals["map_get"] + totals["list_get"]
    error_total = totals["try_catch"]
    agent_total = totals["run_agent"] + totals["run_parallel"]
    return [
        "Roadmap mapping",
        (
            f"  Record retrieval boilerplate: {retrieval_total} "
            f"(find={totals['find']} list_length={totals['list_length']} "
            f"list_get={totals['list_get']} index_math={totals['index_math']})"
        ),
        (
            f"  Storage boilerplate: {storage_total} "
            f"(state_writes={totals['set_state']} create={totals['create']} delete={totals['delete']})"
        ),
        (
            f"  Data access boilerplate: {data_access_total} "
            f"(map_get={totals['map_get']} list_get={totals['list_get']})"
        ),
        f"  Error boilerplate: {error_total} (try_catch={totals['try_catch']})",
        f"  Agent verbosity: {agent_total} (run_agent={totals['run_agent']} run_parallel={totals['run_parallel']})",
    ]

__all__ = ["analyze_files", "analyze_path", "render_json", "render_text"]
