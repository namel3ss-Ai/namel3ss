from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pytest

from namel3ss.ui.manifest import build_manifest
from tests.conftest import lower_ir_program
from tools.docs_example_extract import DocsExample, default_doc_paths, load_examples


FLOW_DEF_RE = re.compile(r'^\s*flow\s+"([^"]+)"', re.MULTILINE)
FLOW_REF_RE = re.compile(r'(?:calls|sends\s+to|send\s+to)\s+flow\s+"([^"]+)"')
RECORD_DEF_RE = re.compile(r'^\s*record\s+"([^"]+)"', re.MULTILINE)
RECORD_REF_RE = re.compile(
    r'\b(?:table|form|list|chart)\s+is\s+"([^"]+)"|\bview\s+of\s+"([^"]+)"',
    re.IGNORECASE,
)

MESSAGES_RE = re.compile(r'messages\s+from\s+(?:is\s+)?state\.([A-Za-z0-9_.]+)')
CITATIONS_RE = re.compile(r'citations\s+from\s+(?:is\s+)?state\.([A-Za-z0-9_.]+)')
MEMORY_RE = re.compile(r'memory\s+from\s+is\s+state\.([A-Za-z0-9_.]+)')
THINKING_RE = re.compile(r'thinking\s+when\s+(?:is\s+)?state\.([A-Za-z0-9_.]+)')
SCOPE_SELECTOR_RE = re.compile(
    r'scope_selector\s+from\s+state\.([A-Za-z0-9_.]+)\s+active\s+in\s+state\.([A-Za-z0-9_.]+)'
)
TRUST_INDICATOR_RE = re.compile(r'trust_indicator\s+from\s+state\.([A-Za-z0-9_.]+)')
SOURCE_PREVIEW_RE = re.compile(r'source_preview\s+from\s+state\.([A-Za-z0-9_.]+)')
TABLE_FROM_STATE_RE = re.compile(r'table\s+from\s+state\.?([A-Za-z0-9_.]+)')
LIST_FROM_STATE_RE = re.compile(r'list\s+from\s+state\.?([A-Za-z0-9_.]+)')
CHART_FROM_STATE_RE = re.compile(r'chart\s+from\s+(?:is\s+)?state\.?([A-Za-z0-9_.]+)')

STATE_PATH_RE = re.compile(r'state\.([A-Za-z0-9_.]+)')
STRING_COMP_RE = re.compile(r'state\.([A-Za-z0-9_.]+)\s*(?:==|is|!=)\s*"([^"]*)"')
BOOL_COMP_RE = re.compile(r'state\.([A-Za-z0-9_.]+)\s*(?:==|is|!=)\s*(true|false)\b', re.IGNORECASE)
NUM_COMP_RE = re.compile(r'state\.([A-Za-z0-9_.]+)\s*(?:==|is|>=|<=|>|<)\s*(-?\d+(?:\.\d+)?)')
IN_LIST_RE = re.compile(r'state\.([A-Za-z0-9_.]+)\s*(?:in|not\s+in)\s*\[([^\]]+)\]')
EMPTY_RE = re.compile(r'state\.([A-Za-z0-9_.]+)\s+is\s+empty')


def test_docs_examples_compile(tmp_path: Path) -> None:
    paths = default_doc_paths(Path("."))
    examples = load_examples(paths)
    assert examples, "No docs examples found to compile."

    for example in examples:
        _compile_docs_example(example, base_tmp=tmp_path)


def test_docs_example_compile_error_reporting(tmp_path: Path) -> None:
    broken = DocsExample(
        path=Path("docs/ui-dsl.md"),
        index=99,
        start_line=12,
        end_line=13,
        language="ai",
        source='page "broken":\n  table is',
    )
    with pytest.raises(AssertionError) as excinfo:
        _compile_docs_example(broken, base_tmp=tmp_path)

    text = str(excinfo.value)
    assert "docs/ui-dsl.md" in text
    assert "example 99" in text
    assert "12-13" in text
    assert "What happened" in text


def _compile_docs_example(example: DocsExample, *, base_tmp: Path) -> None:
    source = _inject_missing_definitions(example.source)
    state = _build_state_for_example(source)
    sandbox = _sandbox_dir(base_tmp, example)
    sandbox.mkdir(parents=True, exist_ok=True)
    app_path = sandbox / "app.ai"
    app_path.write_text(source.rstrip() + "\n", encoding="utf-8")

    try:
        program = lower_ir_program(app_path.read_text(encoding="utf-8"))
        build_manifest(program, state=state, store=None)
    except Exception as exc:  # pragma: no cover - failure surface
        line_range = f"{example.start_line}-{example.end_line}"
        raise AssertionError(
            f"Docs example failed: {example.path.as_posix()}:{line_range} (example {example.index})\n{exc}"
        ) from exc


def _sandbox_dir(base_tmp: Path, example: DocsExample) -> Path:
    digest = hashlib.sha256(f"{example.path}:{example.index}".encode("utf-8")).hexdigest()[:8]
    stem = example.path.stem.replace(".", "_")
    return base_tmp / ".namel3ss" / "docs_examples" / f"{stem}_{example.index:03d}_{digest}"


def _inject_missing_definitions(source: str) -> str:
    defined_flows = set(FLOW_DEF_RE.findall(source))
    referenced_flows = set(FLOW_REF_RE.findall(source))
    missing_flows = sorted(referenced_flows - defined_flows)

    defined_records = set(RECORD_DEF_RE.findall(source))
    referenced_records = _collect_record_refs(source)
    missing_records = sorted(referenced_records - defined_records)

    record_blocks = [_record_stub(name) for name in missing_records]
    flow_blocks = [_flow_stub(name) for name in missing_flows]
    if not record_blocks and not flow_blocks:
        return source

    lines = source.splitlines()
    insert_at = 0
    for idx, line in enumerate(lines):
        if not line.strip():
            continue
        if line.strip().startswith('spec is "'):
            insert_at = idx + 1
        break

    prefix = "\n".join(lines[:insert_at]).rstrip()
    suffix = "\n".join(lines[insert_at:]).lstrip("\n")
    parts = []
    if prefix:
        parts.append(prefix)
    parts.extend(record_blocks)
    parts.extend(flow_blocks)
    if suffix:
        parts.append(suffix)
    return "\n\n".join(parts).rstrip() + "\n"


def _collect_record_refs(source: str) -> set[str]:
    names: set[str] = set()
    for match in RECORD_REF_RE.finditer(source):
        for group in match.groups():
            if group:
                names.add(group)
    return names


def _record_stub(name: str) -> str:
    return f'record "{name}":\n  id text'


def _flow_stub(name: str) -> str:
    return f'flow "{name}":\n  return "ok"'


def _build_state_for_example(source: str) -> dict:
    state: dict = {}

    for path in MESSAGES_RE.findall(source):
        _set_path_if_missing(state, path, [{"role": "user", "content": "Hello"}])

    for path in CITATIONS_RE.findall(source):
        _set_path_if_missing(
            state,
            path,
            [
                {
                    "title": "Spec",
                    "url": "https://example.com/spec",
                    "source_id": "doc-spec",
                }
            ],
        )

    for path in MEMORY_RE.findall(source):
        _set_path_if_missing(state, path, [{"kind": "fact", "text": "Example"}])

    for path in THINKING_RE.findall(source):
        _set_path_if_missing(state, path, False)

    for options_path, active_path in SCOPE_SELECTOR_RE.findall(source):
        _set_path_if_missing(
            state,
            options_path,
            [{"id": "default", "name": "Default scope"}],
        )
        _set_path_if_missing(state, active_path, ["default"])

    for path in TRUST_INDICATOR_RE.findall(source):
        _set_path_if_missing(state, path, True)

    for path in SOURCE_PREVIEW_RE.findall(source):
        _set_path_if_missing(
            state,
            path,
            {
                "title": "Spec",
                "source_id": "doc-spec",
                "snippet": "Example snippet",
            },
        )

    for path in TABLE_FROM_STATE_RE.findall(source):
        _set_path_if_missing(state, path, [])

    for path in LIST_FROM_STATE_RE.findall(source):
        _set_path_if_missing(state, path, [])

    for path in CHART_FROM_STATE_RE.findall(source):
        _set_path_if_missing(state, path, [])

    if "theme_settings_page" in source:
        _set_path_if_missing(state, "ui.settings.size", "normal")
        _set_path_if_missing(state, "ui.settings.radius", "md")

    for path, literal in STRING_COMP_RE.findall(source):
        _set_path_if_missing(state, path, literal)

    for path, literal in BOOL_COMP_RE.findall(source):
        value = literal.lower() == "true"
        _set_path_if_missing(state, path, value)

    for path, literal in NUM_COMP_RE.findall(source):
        value = float(literal) if "." in literal else int(literal)
        _set_path_if_missing(state, path, value)

    for path, values in IN_LIST_RE.findall(source):
        parsed = _parse_list_values(values)
        if parsed:
            _set_path_if_missing(state, path, parsed[0])

    for path in EMPTY_RE.findall(source):
        _set_path_if_missing(state, path, [])

    for path in sorted(set(STATE_PATH_RE.findall(source))):
        _set_path_if_missing(state, path, True)

    return state


def _parse_list_values(values: str) -> list[object]:
    items: list[object] = []
    for raw in values.split(","):
        token = raw.strip()
        if not token:
            continue
        if token.startswith('"') and token.endswith('"'):
            items.append(token[1:-1])
            continue
        if token.lower() in {"true", "false"}:
            items.append(token.lower() == "true")
            continue
        try:
            if "." in token:
                items.append(float(token))
            else:
                items.append(int(token))
            continue
        except ValueError:
            items.append(token)
    return items


def _set_path_if_missing(state: dict, path: str, value: object) -> None:
    parts = [part for part in path.split(".") if part]
    if not parts:
        return
    cursor = state
    for part in parts[:-1]:
        next_cursor = cursor.get(part)
        if not isinstance(next_cursor, dict):
            if part not in cursor:
                cursor[part] = {}
            next_cursor = cursor.get(part)
        if not isinstance(next_cursor, dict):
            return
        cursor = next_cursor
    leaf = parts[-1]
    if leaf in cursor:
        return
    cursor[leaf] = value
