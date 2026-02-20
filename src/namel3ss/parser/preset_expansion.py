from __future__ import annotations

from dataclasses import dataclass
import re

from namel3ss.errors.base import Namel3ssError
from namel3ss.parser.presets import (
    DEFAULT_RAG_CHAT_MODEL,
    DEFAULT_RAG_CHAT_TEMPERATURE,
    RAG_CHAT_TEMPLATE_PLAIN_CONCISE,
    SUPPORTED_RAG_CHAT_ANSWER_TEMPLATES,
    RagChatPresetConfig,
    render_rag_chat_source,
)


_SPEC_LINE_RE = re.compile(r'^spec\s+is\s+"[^"]+"\s*$', re.IGNORECASE)
_USE_PRESET_RE = re.compile(r'^(?P<indent>\s*)use\s+preset\s+"(?P<name>[^"]+)"\s*:\s*$')
_OVERRIDE_FLOW_RE = re.compile(r'^(?P<indent>\s*)override\s+flow\s+"(?P<name>[^"]+)"\s*:\s*$')
_SETTING_LINE_RE = re.compile(r"^(?P<key>[A-Za-z_][A-Za-z0-9_]*)\s+is\s+(?P<value>.+)\s*$")
_SETTING_STRING_RE = re.compile(r'^"(?P<value>.*)"$')
_SETTING_NUMBER_RE = re.compile(r"^-?(?:\d+)(?:\.\d+)?$")
_ASK_INPUT_BLOCK_RE = re.compile(r'^(?P<indent>\s*)ask\s+ai\s+"(?P<ai>[^"]+)"\s+with\s+input:\s*$')
_ASK_INPUT_FIELD_RE = re.compile(r'^(?P<indent>\s*)(?P<key>[A-Za-z_][A-Za-z0-9_]*)\s+is\s+(?P<expr>.+)$')
_RETURN_STMT_RE = re.compile(r'^(?P<indent>\s*)return\s+(?P<expr>.+)$')


@dataclass(frozen=True)
class ParsedPresetBlocks:
    config: RagChatPresetConfig
    override_body: list[str] | None
    remaining_lines: list[str]


def expand_language_presets(source: str) -> str:
    if "use preset" not in source and "override flow" not in source:
        return source
    parsed = _parse_rag_chat_blocks(source)
    if parsed is None:
        return source
    spec_line, trailing = _extract_spec_line(parsed.remaining_lines)
    rendered = render_rag_chat_source(
        spec_line=spec_line,
        config=parsed.config,
        override_body=parsed.override_body,
    )
    if trailing:
        return rendered.rstrip() + "\n\n" + "\n".join(trailing).rstrip() + "\n"
    return rendered


def _parse_rag_chat_blocks(source: str) -> ParsedPresetBlocks | None:
    lines = source.splitlines()
    consumed: set[int] = set()
    preset_config: RagChatPresetConfig | None = None
    override_body: list[str] | None = None
    i = 0
    while i < len(lines):
        line = lines[i]
        preset_match = _USE_PRESET_RE.match(line)
        if preset_match:
            preset_name = str(preset_match.group("name") or "").strip()
            if preset_name != "rag_chat":
                raise Namel3ssError(f'Unknown preset "{preset_name}".')
            if preset_config is not None:
                raise Namel3ssError('Duplicate `use preset "rag_chat"` declarations are not allowed.')
            base_indent = len(preset_match.group("indent") or "")
            block, end = _collect_indented_block(lines, start=i + 1, base_indent=base_indent)
            preset_config = _parse_preset_settings(block)
            consumed.update(range(i, end))
            i = end
            continue

        override_match = _OVERRIDE_FLOW_RE.match(line)
        if override_match:
            flow_name = str(override_match.group("name") or "").strip()
            if flow_name != "rag.answer":
                raise Namel3ssError(f'Unsupported override target "{flow_name}". Only "rag.answer" is supported.')
            if override_body is not None:
                raise Namel3ssError('Duplicate `override flow "rag.answer"` declarations are not allowed.')
            base_indent = len(override_match.group("indent") or "")
            block, end = _collect_indented_block(lines, start=i + 1, base_indent=base_indent)
            override_body = _normalize_override_body(block)
            consumed.update(range(i, end))
            i = end
            continue
        i += 1

    if preset_config is None and override_body is None:
        return None
    if preset_config is None and override_body is not None:
        raise Namel3ssError('`override flow "rag.answer"` requires `use preset "rag_chat":`.')
    remaining = [line for idx, line in enumerate(lines) if idx not in consumed]
    return ParsedPresetBlocks(
        config=preset_config or RagChatPresetConfig(),
        override_body=override_body,
        remaining_lines=remaining,
    )


def _collect_indented_block(lines: list[str], *, start: int, base_indent: int) -> tuple[list[str], int]:
    collected: list[str] = []
    index = start
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if stripped:
            indent = _indent_width(line)
            if indent <= base_indent:
                break
        collected.append(line)
        index += 1
    return collected, index


def _parse_preset_settings(block_lines: list[str]) -> RagChatPresetConfig:
    if not block_lines:
        return RagChatPresetConfig()
    normalized = _dedent_lines(block_lines)
    title = "Assistant"
    accept: str | None = None
    model = DEFAULT_RAG_CHAT_MODEL
    system: str | None = None
    temperature = DEFAULT_RAG_CHAT_TEMPERATURE
    answer_template = RAG_CHAT_TEMPLATE_PLAIN_CONCISE
    for line in normalized:
        stripped = line.strip()
        if not stripped:
            continue
        match = _SETTING_LINE_RE.match(stripped)
        if not match:
            raise Namel3ssError(f"Invalid preset setting line: {stripped}")
        key = str(match.group("key") or "")
        raw_value = str(match.group("value") or "").strip()
        if key == "title":
            title = _expect_quoted_setting(key=key, value=raw_value)
            continue
        if key == "accept":
            accept = _expect_quoted_setting(key=key, value=raw_value)
            continue
        if key == "model":
            model = _expect_quoted_setting(key=key, value=raw_value)
            continue
        if key == "system":
            system = _expect_quoted_setting(key=key, value=raw_value)
            continue
        if key == "temperature":
            if not _SETTING_NUMBER_RE.match(raw_value):
                raise Namel3ssError("rag_chat preset temperature must be a number literal.")
            try:
                temperature = float(raw_value)
            except ValueError as err:
                raise Namel3ssError("rag_chat preset temperature must be a number literal.") from err
            continue
        if key == "answer_template":
            answer_template = _expect_quoted_setting(key=key, value=raw_value)
            if answer_template not in set(SUPPORTED_RAG_CHAT_ANSWER_TEMPLATES):
                supported = ", ".join(sorted(SUPPORTED_RAG_CHAT_ANSWER_TEMPLATES))
                raise Namel3ssError(
                    f'Unknown rag_chat answer_template "{answer_template}". Supported: {supported}.'
                )
            continue
        raise Namel3ssError(f'Unknown rag_chat preset setting "{key}".')
    return RagChatPresetConfig(
        title=title,
        accept=accept,
        model=model,
        system=system,
        temperature=temperature,
        answer_template=answer_template,
    )


def _expect_quoted_setting(*, key: str, value: str) -> str:
    match = _SETTING_STRING_RE.match(value)
    if match is None:
        raise Namel3ssError(f'rag_chat preset setting "{key}" must be a quoted string.')
    return str(match.group("value") or "")


def _normalize_override_body(block_lines: list[str]) -> list[str]:
    if not any(line.strip() for line in block_lines):
        raise Namel3ssError('`override flow "rag.answer"` must include a body.')
    dedented = _dedent_lines(block_lines)
    rewritten = _rewrite_override_ask_blocks(dedented)
    rewritten = _rewrite_override_input_aliases(rewritten)
    return _rewrite_override_returns(rewritten)


def _rewrite_override_ask_blocks(lines: list[str]) -> list[str]:
    rewritten: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        ask_match = _ASK_INPUT_BLOCK_RE.match(line)
        if not ask_match:
            rewritten.append(line)
            i += 1
            continue
        ask_indent = len(ask_match.group("indent") or "")
        ai_name = str(ask_match.group("ai") or "")
        fields, end = _collect_child_lines(lines, start=i + 1, parent_indent=ask_indent)
        if not any(entry.strip() for entry in fields):
            raise Namel3ssError("ask ai input block requires at least one field.")
        rewritten.append(f'{" " * ask_indent}ask ai "{ai_name}" with structured input from map:')
        rewritten.extend(_quote_ask_input_fields(fields))
        i = end
    return rewritten


def _collect_child_lines(lines: list[str], *, start: int, parent_indent: int) -> tuple[list[str], int]:
    collected: list[str] = []
    idx = start
    while idx < len(lines):
        line = lines[idx]
        stripped = line.strip()
        if stripped and _indent_width(line) <= parent_indent:
            break
        collected.append(line)
        idx += 1
    return collected, idx


def _quote_ask_input_fields(lines: list[str]) -> list[str]:
    quoted: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            quoted.append(line)
            continue
        field_match = _ASK_INPUT_FIELD_RE.match(line)
        if not field_match:
            quoted.append(line)
            continue
        indent = str(field_match.group("indent") or "")
        key = str(field_match.group("key") or "")
        expr = str(field_match.group("expr") or "").strip()
        quoted.append(f'{indent}"{key}" is {expr}')
    return quoted


def _rewrite_override_returns(lines: list[str]) -> list[str]:
    non_empty = [line for line in lines if line.strip()]
    top_indent = min((_indent_width(line) for line in non_empty), default=0)
    rewritten: list[str] = []
    replaced = False
    for line in lines:
        return_match = _RETURN_STMT_RE.match(line)
        if return_match and len(return_match.group("indent") or "") == top_indent:
            expr = str(return_match.group("expr") or "").strip()
            rewritten.append(f'{" " * top_indent}set __rag_answer_text is {expr}')
            replaced = True
            continue
        rewritten.append(line)
    if not replaced:
        rewritten.append(f'{" " * top_indent}set __rag_answer_text is input.message')
    return rewritten


def _rewrite_override_input_aliases(lines: list[str]) -> list[str]:
    rewritten: list[str] = []
    for line in lines:
        updated = line.replace("input.context", "context_text")
        updated = updated.replace("input.query", "query_text")
        rewritten.append(updated)
    return rewritten


def _extract_spec_line(lines: list[str]) -> tuple[str, list[str]]:
    spec_line: str | None = None
    remaining: list[str] = []
    for line in lines:
        stripped = line.strip()
        if spec_line is None and _SPEC_LINE_RE.match(stripped):
            spec_line = stripped
            continue
        remaining.append(line)
    if spec_line is None:
        spec_line = 'spec is "1.0"'
    return spec_line, _trim_blank_lines(remaining)


def _dedent_lines(lines: list[str]) -> list[str]:
    non_empty = [line for line in lines if line.strip()]
    if not non_empty:
        return ["" for _ in lines]
    min_indent = min(_indent_width(line) for line in non_empty)
    dedented: list[str] = []
    for line in lines:
        if not line.strip():
            dedented.append("")
            continue
        dedented.append(line[min_indent:])
    return dedented


def _indent_lines(lines: list[str], *, prefix: str = "  ") -> list[str]:
    return [(prefix + line) if line else "" for line in lines]


def _indent_width(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _trim_blank_lines(lines: list[str]) -> list[str]:
    start = 0
    end = len(lines)
    while start < end and not lines[start].strip():
        start += 1
    while end > start and not lines[end - 1].strip():
        end -= 1
    return lines[start:end]


__all__ = ["expand_language_presets"]
